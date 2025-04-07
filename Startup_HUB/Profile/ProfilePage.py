import reflex as rx
from ..Auth.AuthPage import AuthState
import httpx
import aiohttp

class State(rx.State):
    """State for the profile page."""
    
    # API endpoint
    API_URL = "http://100.95.107.24:8000/api/auth"
    STARTUP_IDEAS_API = "http://100.95.107.24:8000/api/startup-profile/startup-ideas"
    
    # Basic Info
    name: str = ""
    first_name: str = ""
    last_name: str = ""
    career_summary: str = ""  # Changed from job_title to match API
    experience: str = ""  # Changed from experience_level to match API
    industry: str = ""  # Changed from category to match API
    
    # Profile Picture
    profile_picture_url: str = ""
    
    # Startup Ideas
    startup_ideas: list = []
    show_startup_modal: bool = False
    editing_startup: dict = {}
    
    # Debug information
    auth_debug_result: str = ""
    
    # Profile username (different from route parameter)
    profile_username: str = ""
    
    @rx.var
    def get_username(self) -> str:
        """Get username from route parameters."""
        if not self.profile_username and hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            self.profile_username = params.get("profile_name", "")
        return self.profile_username
    
    @rx.var
    def current_url(self) -> str:
        """Get the current full URL."""
        return self.router.page.full_raw_path

    async def on_mount(self):
        """Load profile data when component mounts."""
        if hasattr(self, "router"):
            # Initialize token from localStorage if needed
            auth_state = await self.get_state(AuthState)
            if not auth_state.token:
                token_from_storage = await rx.call_script("localStorage.getItem('auth_token')")
                if token_from_storage:
                    auth_state.set_token(token_from_storage)
                    print(f"Token initialized from localStorage: {token_from_storage}")
            
            # We can't use AuthState.is_authed directly in if statements
            # Instead, load profile data and let the UI handle auth
            params = getattr(self.router.page, "params", {})
            username = params.get("profile_name", "")
            
            # Get the correct username case from auth debug if available
            if username and auth_state.token:
                try:
                    auth_debug_data = await self.debug_auth_token(auth_state.token)
                    user_data = auth_debug_data.get("user_from_token", {})
                    if user_data and "username" in user_data:
                        # Use the username from the auth debug data to ensure case consistency
                        correct_username = user_data["username"]
                        print(f"Using username from auth debug: {correct_username}")
                        
                        # If the username case doesn't match, redirect to the correct URL
                        if correct_username.lower() != username.lower():
                            print(f"Username case mismatch: {username} vs {correct_username}")
                            return rx.redirect(f"/profile/{correct_username}")
                        
                        username = correct_username
                        
                        # Ensure token is synchronized with the server
                        token_from_header = auth_debug_data.get("token_from_header")
                        if token_from_header and token_from_header != auth_state.token:
                            print(f"Token mismatch detected. Updating token from {auth_state.token} to {token_from_header}")
                            auth_state.set_token(token_from_header)
                            # Update localStorage with the correct token
                            await rx.call_script(f"localStorage.setItem('auth_token', '{token_from_header}')")
                except Exception as e:
                    print(f"Error getting username from auth debug: {e}")
            
            if username:
                self.profile_username = username
                await self.load_profile_data()
            
        await self.load_startup_ideas()
    
    # About section
    bio: str = ""  # Changed from about to match API
    
    # Skills (list for better management)
    skills_list: list[str] = []  # Changed from skills to match API
    
    # Projects (list of projects)
    past_projects_list: list[str] = []  # Changed from projects to match API
    
    # Online presence links
    contact_links: list = []  # Changed from individual links to match API
    
    # Edit mode toggle
    edit_mode: bool = False
    show_edit_form: bool = False

    def set_career_summary(self, value: str):
        """Set the career summary (job title)."""
        self.career_summary = value

    def set_experience(self, value: str):
        """Set the experience level."""
        self.experience = value

    def set_industry(self, value: str):
        """Set the industry."""
        self.industry = value

    def set_bio(self, value: str):
        """Set the bio."""
        self.bio = value

    def set_skills_list(self, value: str):
        """Set the skills list from comma-separated string."""
        self.skills_list = [s.strip() for s in value.split(",") if s.strip()]

    def set_past_projects_list(self, value: str):
        """Set the past projects list from comma-separated string."""
        self.past_projects_list = [p.strip() for p in value.split(",") if p.strip()]

    def format_url(self, url: str) -> str:
        """Format URL to ensure it's valid."""
        if not url:
            return ""
        # Remove any whitespace
        url = url.strip()
        # If URL doesn't start with http:// or https://, add https://
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return url

    def set_contact_links(self, value: str, link_type: str):
        """Set a specific contact link."""
        # Create a new list without the link type we're updating
        new_links = [link for link in self.contact_links if link.get("title") != link_type]
        
        # Add the new link if it has a value
        if value:
            formatted_url = self.format_url(value)
            # Keep the existing id if we're updating an existing link
            existing_link = next((link for link in self.contact_links if link.get("title") == link_type), None)
            new_link = {
                "title": link_type,  # Title will be "Github", "Linkedin", "Portfolio"
                "url": formatted_url
            }
            if existing_link and "id" in existing_link:
                new_link["id"] = existing_link["id"]
            new_links.append(new_link)
        
        self.contact_links = new_links

    @rx.var
    def formatted_skills(self) -> str:
        """Get skills as a comma-separated string."""
        return ",".join(self.skills_list) if self.skills_list else ""

    @rx.var
    def formatted_projects(self) -> str:
        """Get projects as a comma-separated string."""
        return ",".join(self.past_projects_list) if self.past_projects_list else ""

    @rx.var
    def linkedin_link(self) -> str:
        """Get LinkedIn link from contact_links."""
        for link in self.contact_links:
            if link.get("title") == "Linkedin":
                return link.get("url", "")
        return ""

    @rx.var
    def github_link(self) -> str:
        """Get GitHub link from contact_links."""
        for link in self.contact_links:
            if link.get("title") == "Github":
                return link.get("url", "")
        return ""

    @rx.var
    def portfolio_link(self) -> str:
        """Get Portfolio link from contact_links."""
        for link in self.contact_links:
            if link.get("title") == "Portfolio":
                return link.get("url", "")
        return ""

    def toggle_edit_mode(self):
        """Toggle edit mode on/off."""
        self.edit_mode = not self.edit_mode

    def toggle_edit_form(self):
        """Toggle edit form visibility."""
        self.show_edit_form = not self.show_edit_form

    async def debug_auth_token(self, token: str):
        """Debug authentication token validity using the auth-debug endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_URL}/auth-debug/",
                    headers={
                        "Authorization": f"Token {token}",
                        "Accept": "application/json"
                    }
                )
                
                print(f"Profile auth debug response: Status {response.status_code}")
                debug_data = response.json() if response.status_code == 200 else {"error": response.text}
                print(f"Profile auth debug data: {debug_data}")
                
                # Store debug result
                self.auth_debug_result = f"Auth debug: {debug_data}"
                return debug_data
        except Exception as e:
            print(f"Error in profile debug_auth_token: {e}")
            self.auth_debug_result = f"Auth debug error: {str(e)}"
            return {"error": str(e)}

    def handle_auth_error(self):
        """Handle authentication errors by redirecting to login."""
        # Clear token from state
        AuthState.token = ""
        
        # Clear token from localStorage and redirect
        return rx.call_script("""
            localStorage.removeItem('auth_token');
            window.location.href = '/login';
        """)

    def check_auth(self):
        """Check if user is authenticated using localStorage."""
        return rx.call_script("""
            const token = localStorage.getItem('auth_token');
            if (!token) {
                window.location.href = '/login';
                return false;
            }
            return true;
        """)

    async def load_profile_data(self):
        """Load profile data based on the username from the URL."""
        if self.profile_username:
            try:
                # Get token from AuthState
                auth_state = await self.get_state(AuthState)
                auth_token = auth_state.token
                
                # If token is None, try to get it from localStorage
                if not auth_token:
                    auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                    if auth_token:
                        # Update AuthState with the token from localStorage
                        auth_state.set_token(auth_token)
                
                print(f"Retrieved auth token from AuthState: {auth_token}")
                
                # Debug the token to get the correct username case
                try:
                    auth_debug_data = await self.debug_auth_token(auth_token)
                    user_data = auth_debug_data.get("user_from_token", {})
                    if user_data and "username" in user_data:
                        # Use the username from the auth debug data to ensure case consistency
                        correct_username = user_data["username"]
                        print(f"Using username from auth debug: {correct_username}")
                        
                        # If the username case doesn't match, update it
                        if correct_username.lower() != self.profile_username.lower():
                            print(f"Username case mismatch: {self.profile_username} vs {correct_username}")
                            self.profile_username = correct_username
                except Exception as e:
                    print(f"Debug token error: {e}")
                
                # Use httpx to make the request directly from the server
                try:
                    async with httpx.AsyncClient() as client:
                        # Get the headers
                        headers = {
                            "Content-Type": "application/json",
                            "Authorization": f"Token {auth_token}"
                        }
                        
                        # Make the request with the correct username case
                        response = await client.get(
                            f"{self.API_URL}/profile/{self.profile_username}/",
                            headers=headers,
                            follow_redirects=True
                        )
                        
                        print(f"Profile API Response: {response.status_code}")
                        
                        if response.status_code == 200:
                            # Process the response data
                            data = response.json()
                            print(f"Received profile data: {data}")
                            
                            # Update profile picture URL
                            self.profile_picture_url = data.get("profile_picture_url", "")
                            AuthState.profile_picture = self.profile_picture_url
                            
                            # Update basic info - handle null values properly
                            self.first_name = data.get("first_name") or ""
                            self.last_name = data.get("last_name") or ""
                            self.name = f"{self.first_name} {self.last_name}".strip() or "No Name"
                            
                            # Handle field name differences
                            self.career_summary = data.get("career_summary") or "No Job Title"
                            self.experience = data.get("experience_level") or data.get("experience") or "Not Specified"
                            self.industry = data.get("category") or data.get("industry") or "Not Specified"
                            self.bio = data.get("about") or data.get("bio") or ""
                            
                            # Handle skills - ensure null data shows properly
                            skills_data = data.get("skills") or []
                            if isinstance(skills_data, list):
                                self.skills_list = skills_data
                            elif isinstance(skills_data, str):
                                # Handle case where skills might be a comma-separated string
                                self.skills_list = [s.strip() for s in skills_data.split(",") if s.strip()]
                            else:
                                self.skills_list = []
                            
                            # Handle projects - ensure null data shows properly
                            projects_data = data.get("projects") or data.get("past_projects") or []
                            if isinstance(projects_data, list):
                                self.past_projects_list = projects_data
                            elif isinstance(projects_data, str):
                                # Handle case where projects might be a comma-separated string
                                self.past_projects_list = [p.strip() for p in projects_data.split(",") if p.strip()]
                            else:
                                self.past_projects_list = []
                                
                            # Handle contact links
                            self.contact_links = data.get("contact_links", [])
                        elif response.status_code == 404:
                            # Profile doesn't exist yet, create it
                            print(f"Profile for {self.profile_username} doesn't exist yet. Creating it...")
                            
                            # Get user data from auth debug
                            auth_debug_data = await self.debug_auth_token(auth_token)
                            user_data = auth_debug_data.get("user_from_token", {})
                            
                            # Create a new profile
                            create_response = await client.put(
                                f"{self.API_URL}/profile/{self.profile_username}/",
                                headers=headers,
                                json={
                                    "username": self.profile_username,
                                    "first_name": user_data.get("first_name", ""),
                                    "last_name": user_data.get("last_name", ""),
                                    "email": user_data.get("email", ""),
                                    "bio": "",
                                    "industry": "Not Specified",
                                    "experience": "Not Specified",
                                    "skills": user_data.get("skills", ""),
                                    "contact_links": []
                                }
                            )
                            
                            print(f"Profile creation response: {create_response.status_code}")
                            
                            if create_response.status_code in [200, 201]:
                                # Profile created successfully, load it
                                print("Profile created successfully. Loading profile data...")
                                return await self.load_profile_data()
                            else:
                                print(f"Error creating profile: {create_response.text}")
                        elif response.status_code == 401:
                            print(f"Authentication error: {response.status_code}")
                            # Use a non-event-handler function to redirect for auth errors
                            return self.handle_auth_error()
                        else:
                            print(f"Error fetching profile data: {response.status_code}")
                except Exception as e:
                    print(f"Error in httpx request: {e}")
                    
            except Exception as e:
                print(f"Error in load_profile_data: {str(e)}")

    def logout(self):
        """Log out by clearing the authentication token and redirecting to login."""
        # Use AuthState's logout method to properly clear the token
        AuthState.clear_token()
        return rx.redirect("/login")

    async def save_changes(self, form_data: dict):
        """Save profile changes to the API."""
        # Update profile data from form
        self.first_name = form_data.get("first_name", self.first_name)
        self.last_name = form_data.get("last_name", self.last_name)
        self.career_summary = form_data.get("career_summary", self.career_summary)
        self.bio = form_data.get("about", self.bio)
        self.industry = form_data.get("category", self.industry)
        self.experience = form_data.get("experience_level", self.experience)
        
        # Update contact links from form data
        self.contact_links = []
        
        # Add links from form data
        if form_data.get("linkedin_link"):
            self.contact_links.append({
                "title": "Linkedin",  # Exact title from API
                "url": self.format_url(form_data.get("linkedin_link"))
            })
        if form_data.get("github_link"):
            self.contact_links.append({
                "title": "Github",  # Exact title from API
                "url": self.format_url(form_data.get("github_link"))
            })
        if form_data.get("portfolio_link"):
            self.contact_links.append({
                "title": "Portfolio",  # Exact title from API
                "url": self.format_url(form_data.get("portfolio_link"))
            })
        
        # Update skills from form data
        skills_value = form_data.get("skills", "")
        if skills_value:
            self.skills_list = [s.strip() for s in skills_value.split(",") if s.strip()]
        
        # Update projects from form data
        projects_value = form_data.get("projects", "")
        if projects_value:
            self.past_projects_list = [p.strip() for p in projects_value.split(",") if p.strip()]
        
        # Compose full name
        self.name = f"{self.first_name} {self.last_name}".strip() or "No Name"
        
        # Get token from AuthState
        auth_state = await self.get_state(AuthState)
        auth_token = auth_state.token
        
        # If token is not in AuthState, try to get it from localStorage
        if not auth_token:
            auth_token = await rx.call_script("localStorage.getItem('auth_token')")
            if auth_token:
                # Update AuthState with the token from localStorage
                auth_state.set_token(auth_token)
            else:
                # If no token found, redirect to login
                return self.handle_auth_error()
        
        # Get the correct username case from auth debug
        try:
            auth_debug_data = await self.debug_auth_token(auth_token)
            user_data = auth_debug_data.get("user_from_token", {})
            if user_data and "username" in user_data:
                # Use the username from the auth debug data to ensure case consistency
                correct_username = user_data["username"]
                print(f"Using username from auth debug for update: {correct_username}")
                
                # If the username case doesn't match, update it
                if correct_username.lower() != self.profile_username.lower():
                    print(f"Username case mismatch for update: {self.profile_username} vs {correct_username}")
                    self.profile_username = correct_username
        except Exception as e:
            print(f"Debug token error during update: {e}")
        
        # Create profile data for API - map to correct field names
        profile_data = {
            "id": None,  # Will be set by the API
            "username": self.profile_username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": user_data.get("email", ""),  # Get email from auth debug data
            "profile_picture_url": self.profile_picture_url,
            "bio": self.bio,
            "industry": self.industry,
            "experience": self.experience,
            "skills": ",".join(self.skills_list) if self.skills_list else "",
            "past_projects": ",".join(self.past_projects_list) if self.past_projects_list else "",
            "career_summary": self.career_summary,  # Using job_title as career_summary
            "contact_links": self.contact_links
        }
        
        # Define headers here
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {auth_token}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # First get the existing profile data
                get_response = await client.get(
                    f"{self.API_URL}/profile/{self.profile_username}/",
                    headers=headers
                )
                
                if get_response.status_code == 200:
                    existing_data = get_response.json()
                    # Preserve existing fields that we're not updating
                    for key in existing_data:
                        if key not in profile_data:
                            profile_data[key] = existing_data[key]
                
                # First try to get the profile to see if it exists
                get_response = await client.get(
                    f"{self.API_URL}/profile/{self.profile_username}/",
                    headers=headers
                )
                
                print(f"GET Profile Response: {get_response.status_code}")
                print(f"GET Profile Data: {get_response.text}")
                
                if get_response.status_code == 404:
                    # Profile doesn't exist, create it using PUT
                    create_response = await client.put(
                        f"{self.API_URL}/profile/{self.profile_username}/",
                        json=profile_data,
                        headers=headers
                    )
                    
                    print(f"Create Profile Request Data: {profile_data}")
                    print(f"Create Profile Response: {create_response.status_code}")
                    print(f"Create Profile Response Data: {create_response.text}")
                    
                    if create_response.status_code in [200, 201]:
                        print("Profile created successfully")
                        self.show_edit_form = False
                        await self.load_profile_data()
                    else:
                        print(f"Error creating profile: {create_response.text}")
                        print(f"Response status: {create_response.status_code}")
                        print(f"Response headers: {create_response.headers}")
                else:
                    # Profile exists, update it
                    update_response = await client.put(
                        f"{self.API_URL}/profile/{self.profile_username}/",
                        json=profile_data,
                        headers=headers
                    )
                    
                    print(f"Update Profile Request Data: {profile_data}")
                    print(f"Update Profile Response: {update_response.status_code}")
                    print(f"Update Profile Response Data: {update_response.text}")
                    
                    if update_response.status_code in [200, 201]:
                        print("Profile updated successfully")
                        self.show_edit_form = False
                        # Reload profile data to ensure UI is updated
                        await self.load_profile_data()
                    else:
                        print(f"Error updating profile: {update_response.text}")
                        print(f"Response status: {update_response.status_code}")
                        print(f"Response headers: {update_response.headers}")
                        
        except Exception as e:
            print(f"Error saving profile changes: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
        
        # Close the form modal
        self.show_edit_form = False

    def cancel_edit(self):
        """Cancel editing."""
        self.show_edit_form = False

    @rx.var
    def has_about(self) -> bool:
        """Check if about text exists."""
        return len(self.bio) > 0

    async def load_startup_ideas(self):
        """Load startup ideas for the current user."""
        try:
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.STARTUP_IDEAS_API}/my-ideas/?username={self.profile_username}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    # Extract the results array from the response
                    data = response.json()
                    self.startup_ideas = data.get('results', [])
                elif response.status_code == 404:
                    self.startup_ideas = []
                else:
                    print(f"Error loading startup ideas: {response.text}")
        except Exception as e:
            print(f"Error in load_startup_ideas: {e}")
            self.startup_ideas = []

    async def save_startup_idea(self, form_data: dict):
        """Save a new or updated startup idea."""
        try:
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            startup_data = {
                "name": form_data.get("name", ""),
                "stage": form_data.get("stage", "IDEA"),
                "user_role": form_data.get("user_role", "FOUNDER"),
                "pitch": form_data.get("pitch", ""),
                "description": form_data.get("description", ""),
                "skills": form_data.get("skills", "").split(",") if form_data.get("skills") else [],
                "looking_for": form_data.get("looking_for", "").split(",") if form_data.get("looking_for") else [],
                "pitch_deck": form_data.get("pitch_deck", ""),
                "website": form_data.get("website", ""),
                "funding_stage": form_data.get("funding_stage", "Pre-seed"),
                "investment_needed": float(form_data.get("investment_needed", 0)) if form_data.get("investment_needed") else None
            }
            
            async with httpx.AsyncClient() as client:
                if self.editing_startup:
                    # Update existing idea
                    response = await client.put(
                        f"{self.STARTUP_IDEAS_API}/my-ideas/{self.editing_startup.get('id')}/",
                        json=startup_data,
                        headers=headers
                    )
                else:
                    # Create new idea
                    response = await client.post(
                        f"{self.STARTUP_IDEAS_API}/my-ideas/",
                        json=startup_data,
                        headers=headers
                    )
                
                if response.status_code in [200, 201]:
                    self.show_startup_modal = False
                    self.editing_startup = {}
                    await self.load_startup_ideas()
                else:
                    print(f"Error saving startup idea: {response.text}")
        except Exception as e:
            print(f"Error in save_startup_idea: {e}")

    def toggle_startup_modal(self):
        """Toggle the startup idea modal."""
        self.show_startup_modal = not self.show_startup_modal
        if not self.show_startup_modal:
            self.editing_startup = {}

    def edit_startup(self, startup: dict):
        """Start editing a startup idea."""
        self.editing_startup = startup
        self.show_startup_modal = True

    async def delete_startup(self, startup_id: str):
        """Delete a startup idea."""
        try:
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.STARTUP_IDEAS_API}/my-ideas/{startup_id}/",
                    headers=headers
                )
                
                if response.status_code == 204:
                    await self.load_startup_ideas()
                else:
                    print(f"Error deleting startup idea: {response.text}")
        except Exception as e:
            print(f"Error in delete_startup: {e}")

    async def upload_profile_picture(self, files: list[rx.UploadFile]):
        """Upload a new profile picture."""
        print("\n" + "="*50)
        print("🚀 STARTING PROFILE PICTURE UPLOAD")
        print("="*50 + "\n")
        
        if not files or len(files) == 0:
            print("❌ ERROR: No files received")
            return
        
        try:
            # Get the first file from the list
            file = files[0]
            print(f"\n📁 FILE INFORMATION:")
            print(f"  - Filename: {file.filename}")
            print(f"  - Content Type: {file.content_type}")
            
            # Read the file content
            content = await file.read()
            print(f"\n📦 FILE CONTENT:")
            print(f"  - Content Length: {len(content)} bytes")
            
            # Get auth token
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                print("\n❌ ERROR: No auth token found")
                return
            print(f"\n🔑 AUTH TOKEN: {auth_token[:10]}...")
            
            # Create form data with just the profile picture
            form = aiohttp.FormData()
            form.add_field('profile_picture',
                         content,
                         filename=file.filename,
                         content_type='image/jpeg' if file.filename.lower().endswith(('.jpg', '.jpeg')) else 'image/png')
            
            print("\n📤 UPLOADING PROFILE PICTURE...")
            # Make the request to update profile with new image
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.API_URL}/profile/",
                    data=form,
                    headers={
                        "Authorization": f"Token {auth_token}",
                        "Accept": "application/json",
                        "Content-Type": "multipart/form-data"
                    }
                ) as response:
                    print(f"\n📥 UPLOAD RESPONSE:")
                    print(f"  - Status: {response.status}")
                    response_text = await response.text()
                    print(f"  - Response: {response_text}")
                    
                    if response.status == 200:
                        # Update the profile picture in the state
                        data = await response.json()
                        if "profile_picture_url" in data:
                            print("\n✅ SUCCESS:")
                            print(f"  - New URL: {data['profile_picture_url']}")
                            self.profile_picture_url = data["profile_picture_url"]
                            AuthState.profile_picture = self.profile_picture_url
                            # Reload the profile data to ensure everything is in sync
                            await self.load_profile_data()
                        else:
                            print("\n❌ ERROR: No profile_picture_url in response")
                    else:
                        print(f"\n❌ ERROR uploading profile picture: {response_text}")
        
        except Exception as e:
            print(f"\n❌ ERROR in upload_profile_picture: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            
        finally:
            print("\n" + "="*50)
            print("🏁 END OF PROFILE PICTURE UPLOAD")
            print("="*50 + "\n")
            
            # Keep the edit form open
            self.show_edit_form = True
            
            # Force a re-render of the form
            await self.get_state(AuthState)
            
            # Add a small delay to ensure the form stays open
            await rx.sleep(0.1)

def skill_badge(skill: str) -> rx.Component:
    """Create a badge for a skill."""
    return rx.badge(
        skill,
        class_name="bg-gray-100 text-gray-800 px-3 py-1 rounded-lg m-1"
    )

def project_badge(project: str) -> rx.Component:
    """Create a badge for a project."""
    return rx.badge(
        project,
        class_name="bg-gray-100 text-gray-800 px-3 py-1 rounded-lg m-1"
    )

def startup_idea_modal() -> rx.Component:
    """Render the startup idea modal."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                "Startup Idea",
                class_name="text-3xl font-bold mb-4 text-blue-600",
            ),
            rx.form(
                rx.vstack(
                    rx.input(
                        placeholder="Startup Name",
                        name="name",
                        required=True,
                        default_value=rx.cond(
                            State.editing_startup,
                            State.editing_startup.get("name", ""),
                            ""
                        ),
                        class_name="w-full p-2 border rounded-lg bg-white",
                    ),
                    rx.select(
                        ["IDEA", "MVP", "BETA", "LAUNCHED", "SCALING"],
                        placeholder="Stage",
                        name="stage",
                        default_value=rx.cond(
                            State.editing_startup,
                            State.editing_startup.get("stage", "IDEA"),
                            "IDEA"
                        ),
                        class_name="w-full p-2 border rounded-lg bg-white",
                    ),
                    rx.select(
                        ["FOUNDER", "CO-FOUNDER", "TEAM_MEMBER", "INVESTOR", "ADVISOR"],
                        placeholder="Your Role",
                        name="user_role",
                        default_value=rx.cond(
                            State.editing_startup,
                            State.editing_startup.get("user_role", "FOUNDER"),
                            "FOUNDER"
                        ),
                        class_name="w-full p-2 border rounded-lg bg-white",
                    ),
                    rx.text_area(
                        placeholder="Elevator Pitch",
                        name="pitch",
                        default_value=rx.cond(
                            State.editing_startup,
                            State.editing_startup.get("pitch", ""),
                            ""
                        ),
                        class_name="w-full p-2 border rounded-lg bg-white",
                    ),
                    rx.text_area(
                        placeholder="Description",
                        name="description",
                        default_value=rx.cond(
                            State.editing_startup,
                            State.editing_startup.get("description", ""),
                            ""
                        ),
                        class_name="w-full p-2 border rounded-lg bg-white",
                    ),
                    rx.input(
                        placeholder="Skills (comma-separated)",
                        name="skills",
                        default_value=rx.cond(
                            State.editing_startup,
                            ",".join(State.editing_startup.get("skills", [])),
                            ""
                        ),
                        class_name="w-full p-2 border rounded-lg bg-white",
                    ),
                    rx.input(
                        placeholder="Looking for (comma-separated)",
                        name="looking_for",
                        default_value=rx.cond(
                            State.editing_startup,
                            ",".join(State.editing_startup.get("looking_for", [])),
                            ""
                        ),
                        class_name="w-full p-2 border rounded-lg bg-white",
                    ),
                    rx.input(
                        placeholder="Pitch Deck URL",
                        name="pitch_deck",
                        default_value=rx.cond(
                            State.editing_startup,
                            State.editing_startup.get("pitch_deck", ""),
                            ""
                        ),
                        class_name="w-full p-2 border rounded-lg bg-white",
                    ),
                    rx.input(
                        placeholder="Website URL",
                        name="website",
                        default_value=rx.cond(
                            State.editing_startup,
                            State.editing_startup.get("website", ""),
                            ""
                        ),
                        class_name="w-full p-2 border rounded-lg bg-white",
                    ),
                    rx.select(
                        ["Pre-seed", "Seed", "Early", "Growth", "Expansion", "Exit"],
                        placeholder="Funding Stage",
                        name="funding_stage",
                        default_value=rx.cond(
                            State.editing_startup,
                            State.editing_startup.get("funding_stage", "Pre-seed"),
                            "Pre-seed"
                        ),
                        class_name="w-full p-2 border rounded-lg bg-white",
                    ),
                    rx.input(
                        placeholder="Investment Needed",
                        name="investment_needed",
                        type="number",
                        default_value=rx.cond(
                            State.editing_startup,
                            str(State.editing_startup.get("investment_needed", 0)),
                            "0"
                        ),
                        class_name="w-full p-2 border rounded-lg bg-white",
                    ),
                    rx.hstack(
                        rx.button(
                            "Cancel",
                            on_click=State.toggle_startup_modal,
                            class_name="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg",
                        ),
                        rx.button(
                            "Save",
                            type="submit",
                            class_name="px-6 py-2 bg-sky-600 text-white hover:bg-sky-700 rounded-lg",
                        ),
                        spacing="4",
                        justify="end",
                        width="100%",
                    ),
                    spacing="4",
                ),
                on_submit=State.save_startup_idea,
            ),
            class_name="bg-white p-8 rounded-xl shadow-2xl border border-gray-200",
        ),
        open=State.show_startup_modal,
    )

def startup_idea_card(startup: dict) -> rx.Component:
    """Render a startup idea card."""
    return rx.box(
        rx.vstack(
            rx.heading(startup.get("name", ""), size="5"),
            rx.text(startup.get("pitch", ""), noOfLines=2),
            rx.hstack(
                rx.badge(startup.get("stage", ""), class_name="bg-blue-100 text-blue-800"),
                rx.badge(startup.get("funding_stage", ""), class_name="bg-green-100 text-green-800"),
                spacing="2",
            ),
            rx.hstack(
                rx.button(
                    "Edit",
                    on_click=lambda: State.edit_startup(startup),
                    class_name="px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700",
                ),
                rx.button(
                    "Delete",
                    on_click=lambda: State.delete_startup(startup.get("id")),
                    class_name="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700",
                ),
                spacing="2",
            ),
            class_name="bg-white p-4 rounded-lg shadow",
        ),
    )

def profile_display() -> rx.Component:
    """Render the profile display component."""
    return rx.box(
        rx.vstack(
            # Header with profile image and basic info
            rx.hstack(
                # Profile Image
                rx.image(
                    src=rx.cond(
                        AuthState.profile_picture,
                        AuthState.profile_picture,
                        "/assets/mock-image.jpg"
                    ),
                    class_name="rounded-full w-24 h-24 object-cover border-2 border-gray-200"
                ),
                # Basic Info
                rx.vstack(
                    rx.heading(State.name, size="8", class_name="text-black font-bold"),
                    rx.hstack(
                        rx.text(f"Job: {State.career_summary}" ,size="5", class_name="text-gray-400"),
                        align_items="center",
                        spacing="2"
                    ),
                    rx.hstack(
                        rx.badge(
                            State.industry,
                            class_name="bg-blue-100 text-blue-800 px-3 py-1 rounded-full"
                        ),
                        rx.badge(
                            State.experience,
                            class_name="bg-green-100 text-green-800 px-3 py-1 rounded-full"
                        ),
                        spacing="2"
                    ),
                    align_items="start",
                    spacing="2"
                ),
                rx.spacer(),
                # Buttons
                rx.hstack(
                    # Edit Profile Button
                    rx.button(
                        rx.icon("pencil", class_name="w-6 h-6"),  # Increased icon size
                        on_click=State.toggle_edit_form,
                        class_name="px-8 py-4 text-lg bg-white text-gray-600 rounded-xl hover:bg-sky-200 hover:text-gray-600 transition-all duration-200"
                    ),
                    # My Projects Button
                    rx.button(
                        "My Projects",
                        on_click=rx.redirect(f"/my-projects/user/{State.profile_username}"),
                        class_name="px-6 py-3 text-lg bg-blue-600 text-white rounded-xl bg-sky-600 hover:bg-sky-500 hover:scale-105 transition-all duration-200 font-bold",
                    ),
                    spacing="4"
                ),
                width="100%",
                padding="4",
                spacing="4"
            ),
            
            # About Section
            rx.box(
                rx.heading("About", size="6", margin_bottom="2" ,class_name="text-sky-500"),
                rx.cond(
                    State.has_about,
                    rx.text(State.bio,class_name="text-gray-400"),
                    rx.text("No description provided.", class_name="text-gray-400 italic")
                ),
                width="100%",
                padding="4",
                class_name="bg-white rounded-lg shadow"
            ),
            
            # Skills Section
            rx.box(
                rx.hstack(
                    rx.heading("Skills", size="6",class_name="text-sky-500"),
                    rx.spacer(),
                    width="100%",
                    margin_bottom="2",
                ),
                rx.flex(
                    rx.foreach(
                        State.skills_list,
                        skill_badge
                    ),
                    wrap="wrap",
                    gap="2",
                    class_name="text-gray-400"
                ),
                width="100%",
                padding="4",
                class_name="bg-white rounded-lg shadow"
            ),

            rx.box(
                rx.hstack(
                    rx.heading("Projects", size="6",class_name="text-sky-500"),
                    rx.spacer(),
                    width="100%",
                    margin_bottom="2",
                ),
                rx.flex(
                    rx.foreach(
                        State.past_projects_list,
                        project_badge
                    ),
                    wrap="wrap",
                    gap="2",
                    class_name="text-gray-400",
                ),
                width="100%",
                padding="4",
                class_name="bg-white rounded-lg shadow"
            ),
            
            # Online Presence Section
            rx.box(
                rx.heading("Online Presence", size="6",class_name="text-sky-500" , margin_bottom="2"),
                rx.vstack(
                    rx.cond(
                        State.linkedin_link != "",
                        rx.hstack(
                            rx.icon("linkedin"),
                            rx.link("LinkedIn", href=State.linkedin_link, is_external=True),
                            class_name="text-blue-600 hover:text-blue-800"
                        ),
                        rx.fragment()
                    ),
                    rx.cond(
                        State.github_link != "",
                        rx.hstack(
                            rx.icon("github"),
                            rx.link("GitHub", href=State.github_link, is_external=True),
                            class_name="text-blue-600 hover:text-blue-800"
                        ),
                        rx.fragment()
                    ),
                    rx.cond(
                        State.portfolio_link != "",
                        rx.hstack(
                            rx.icon("globe"),
                            rx.link("Portfolio", href=State.portfolio_link, is_external=True),
                            class_name="text-blue-600 hover:text-blue-800"
                        ),
                        rx.fragment()
                    ),
                    rx.cond(
                        (State.linkedin_link == "") & (State.github_link == "") & (State.portfolio_link == ""),
                        rx.text("No links provided.", class_name="text-gray-500 italic"),
                        rx.fragment()
                    ),
                    align_items="start",
                    spacing="2"
                ),
                width="100%",
                padding="4",
                class_name="bg-white rounded-lg shadow"
            ),
            
            # Logout button at the bottom right
            rx.box(
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        rx.icon("log-out", class_name="w-7 h-7"),
                        on_click=State.logout,
                        class_name="px-6 py-3 text-lg bg-white text-red-600 rounded-xl hover:bg-red-200 hover:scale-105 transition-all duration-200 font-bold"
                    ),
                ),
                width="100%",
                padding="2",
                margin_top="4"
            ),
            
            width="100%",
            max_width="1000px",
            margin="auto",
            padding="4",
            spacing="4"
        ),
        class_name="bg-white rounded-lg shadow-lg p-6 w-full max-w-6xl mx-auto mt-10"
    )

def edit_form() -> rx.Component:
    """Render the edit form as a modal dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                "Edit Profile", 
                class_name="text-3xl font-bold mb-4 text-sky-600",
            ),
            rx.dialog.description(
                rx.form(
                    rx.vstack(
                        # Profile Photo Upload
                        rx.vstack(
                            rx.box(
                                rx.cond(
                                    State.profile_picture_url,
                                    rx.image(
                                        src=State.profile_picture_url,
                                        width="100%",
                                        height="100%",
                                        object_fit="cover",
                                        border_radius="full",
                                    ),
                                    rx.center(
                                        rx.icon("image", color="gray", size=24),
                                        width="100%",
                                        height="100%",
                                        border_radius="full"
                                    )
                                ),
                                width="120px",
                                height="120px",
                                border_radius="full",
                                bg="gray.100",
                                border="2px solid",
                                border_color="gray.200",
                                overflow="hidden"
                            ),
                            rx.upload(
                                rx.button(
                                    rx.hstack(
                                        rx.icon("upload", class_name="mr-2"),
                                        rx.text("Upload profile photo"),
                                    ),
                                    class_name="px-4 py-2 bg-sky-200 text-sky-700 hover:bg-gray-300 rounded-lg mt-2",
                                ),
                                accept={
                                    "image/png": [".png"],
                                    "image/jpeg": [".jpg", ".jpeg"],
                                },
                                max_files=1,
                                on_drop=State.upload_profile_picture,
                                on_click=lambda: State.set_show_edit_form(True),  # Keep form open on click
                            ),
                            align="center",
                            spacing="2",
                            margin_bottom="6"
                        ),
                        
                        # Name Fields
                        rx.hstack(
                            rx.vstack(
                                rx.text("First Name", align="left", width="100%" ,font_weight="bold", size = "5" , class_name="text-sky-500"),
                                rx.input(
                                    placeholder="First Name",
                                    name="first_name",
                                    required=True,
                                    value=State.first_name,
                                    on_change=lambda value: State.set_first_name(value),
                                    class_name="w-full p-2 border text-black rounded-lg bg-white",
                                ),
                                width="100%",
                                align_items="start"
                            ),
                            rx.vstack(
                                rx.text("Last Name", align="left", width="100%" , font_weight="bold", size = "5" , class_name="text-sky-500"),
                                rx.input(
                                    placeholder="Last Name",
                                    name="last_name",
                                    required=True,
                                    value=State.last_name,
                                    on_change=lambda value: State.set_last_name(value),
                                    class_name="w-full p-2 border rounded-lg bg-white text-black",
                                ),
                                width="100%",
                                align_items="start"
                            ),
                            width="100%",
                            spacing="4"
                        ),
                        
                        # Job Title Field
                        rx.text("Job Title", align="left", width="100%" , font_weight="bold", size = "5" , class_name="text-sky-500"),
                        rx.input(
                            placeholder="Your job title",
                            name="career_summary",
                            value=State.career_summary,
                            on_change=State.set_career_summary,
                            class_name="w-full p-2 border rounded-lg bg-white text-black",
                        ),
                        
                        # Industry & Experience
                        rx.hstack(
                            rx.vstack(
                                rx.text("Industry", align="left", width="100%", font_weight="bold", size = "5" , class_name="text-sky-500"),
                                rx.select(
                                    ["Technology", "Finance", "Healthcare", "Education", "E-commerce", "Other"],
                                    placeholder="Select industry",
                                    name="category",
                                    value=State.industry,
                                    on_change=State.set_industry,
                                    class_name="w-full p-2 border rounded-lg bg-white text-black",
                                ),
                                width="100%",
                                align_items="start"
                            ),
                            rx.vstack(
                                rx.text("Years of Experience", align="left", width="100%", font_weight="bold", size = "5" , class_name="text-sky-500"),
                                rx.select(
                                    ["< 1 year", "1-3 years", "3-5 years", "5-10 years", "10+ years"],
                                    placeholder="Select experience",
                                    name="experience_level",
                                    value=State.experience,
                                    on_change=State.set_experience,
                                    class_name="w-full p-2 border rounded-lg bg-white text-black",
                                ),
                                width="100%",
                                align_items="start"
                            ),
                            width="100%",
                            spacing="4"
                        ),
                        
                        # About Section
                        rx.text("About", align="left", width="100%" , font_weight="bold", size = "5" , class_name="text-sky-500"),
                        rx.text_area(
                            placeholder="Tell us about yourself...",
                            name="about",
                            value=State.bio,
                            on_change=State.set_bio,
                            height="120px",
                            class_name="w-full p-2 border rounded-lg bg-white text-black",
                        ),
                        
                        # Skills Section
                        rx.text("Skills", align="left", width="100%", margin_top="4" , font_weight="bold", size = "5" , class_name="text-sky-500"),
                        rx.input(
                            placeholder="Skills (comma-separated)",
                            name="skills",
                            value=State.formatted_skills,
                            on_change=State.set_skills_list,
                            class_name="w-full p-2 border rounded-lg bg-white text-black",
                        ),
                        
                        # Projects Section
                        rx.text("Projects", align="left", width="100%", margin_top="4" , font_weight="bold", size = "5" , class_name="text-sky-500"),
                        rx.input(
                            placeholder="Projects (comma-separated)",
                            name="projects",
                            value=State.formatted_projects,
                            on_change=State.set_past_projects_list,
                            class_name="w-full p-2 border rounded-lg bg-white text-black",
                        ),
                        
                        # Online Presence
                        rx.text("Online Presence", align="left", width="100%", margin_top="4" , font_weight="bold", size = "5" , class_name="text-sky-500"),
                        rx.hstack(
                            rx.icon("linkedin", color="black"),
                            rx.input(
                                placeholder="LinkedIn URL",
                                name="linkedin_link",
                                value=State.linkedin_link,
                                on_change=lambda value: State.set_contact_links(value, "Linkedin"),  # Exact title
                                class_name="w-full p-2 border rounded-lg bg-white text-black",
                            ),
                            width="100%"
                        ),
                        rx.hstack(
                            rx.icon("github", color="black"),
                            rx.input(
                                placeholder="GitHub URL",
                                name="github_link",
                                value=State.github_link,
                                on_change=lambda value: State.set_contact_links(value, "Github"),  # Exact title
                                class_name="w-full p-2 border rounded-lg bg-white text-black",
                            ),
                            width="100%"
                        ),
                        rx.hstack(
                            rx.icon("globe", color="black"),
                            rx.input(
                                placeholder="Portfolio Website",
                                name="portfolio_link",
                                value=State.portfolio_link,
                                on_change=lambda value: State.set_contact_links(value, "Portfolio"),  # Exact title
                                class_name="w-full p-2 border rounded-lg bg-white text-black",
                            ),
                            width="100%"
                        ),
                        
                        # Buttons
                        rx.hstack(
                            rx.button(
                                "Cancel",
                                on_click=State.cancel_edit,
                                class_name="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg",
                            ),
                            rx.button(
                                "Save Profile",
                                type="submit",
                                class_name="px-6 py-2 bg-sky-600 text-white hover:bg-sky-700 rounded-lg",
                            ),
                            spacing="4",
                            justify="end",
                            width="100%",
                            margin_top="6",
                        ),
                        spacing="6",
                        padding="4",
                    ),
                    on_submit=State.save_changes,
                    reset_on_submit=False,
                ),
                width="100%",
            ),
            max_width="600px",
            width="90vw",
            class_name="bg-white p-8 rounded-xl shadow-2xl border border-gray-200",
        ),
        open=State.show_edit_form,
    )

@rx.page(route="/profile/[profile_name]")
def profile_page() -> rx.Component:
    """Render the profile page."""
    return rx.box(
        rx.center(
            rx.vstack(
                # Auth check on page load
                rx.script("""
                    // Check token on page load
                    const token = localStorage.getItem('auth_token');
                    if (!token) {
                        console.log('No token found - redirecting to login');
                        window.location.href = '/login';
                    } else {
                        console.log('Token found in localStorage:', token);
                        // Update token display
                        const displayElement = document.getElementById('token-display');
                        if (displayElement) {
                            displayElement.textContent = `Token from localStorage: ${token}`;
                        }
                    }
                """),
                
                # Page content
                rx.hstack(
                    rx.heading(
                        "Profile information",
                        size="9",
                        color="white",
                        class_name="mb-4 mt-4 ml-10"
                    ),
                    rx.spacer(),
                    width="100%",
                    class_name="bg-sky-600"
                ),
                
                
                # Profile content
                profile_display(),
                
                # View Matches Button (moved outside of profile display)
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        "View Matches",
                        on_click=rx.redirect(f"/match/from-profile/{State.profile_username}"),
                        class_name="px-9 py-6 text-lg bg-cyan-600 text-white rounded-xl hover:bg-sky-700 hover:scale-110 transition-all duration-200 mt-4 font-bold"
                    ),
                    width="100%",
                    margin_top="4",
                    padding_right="24",
                    justify="end",
                    padding_left="20%",
                    class_name="px-40 py-3"
                ),
                
                # Edit form modal
                edit_form(),
                width="100%",
                padding="4",
            ),
            width="100%",
            padding="4",
            height="100vh"
        ),
        on_mount=State.on_mount,
        class_name="min-h-screen bg-gray-900 py-8 items-center justify-center"
    )

@rx.page(route="/profile")
def base_profile_page() -> rx.Component:
    """Render the base profile page."""
    return rx.box(
        rx.center(
            rx.vstack(
                rx.heading("Please provide a username", size="4", color="white"),
                rx.button(
                    "Go Home",
                    on_click=rx.redirect("/"),
                    class_name="bg-sky-600 text-white px-6 py-2 rounded-lg"
                ),
                padding="8",
            ),
            width="100%",
            padding="4",
            height="100vh"
        ),
        class_name="min-h-screen bg-gray-900 py-8 items-center justify-center"
    )