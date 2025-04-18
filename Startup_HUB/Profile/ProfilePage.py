import reflex as rx
from ..Auth.AuthPage import AuthState
import httpx

class State(rx.State):
    """State for the profile page."""
    
    # API endpoint
    API_URL = "http://100.95.107.24:8000/api/auth"
    
    # Basic Info
    name: str = ""
    first_name: str = ""
    last_name: str = ""
    job_title: str = ""
    experience_level: str = ""
    category: str = ""
    
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
            # else:
            #     return rx.redirect("/")
    
    # About section
    about: str = ""
    
    # Skills (list for better management)
    skills: list[str] = []
    
    # Projects (list of projects)
    projects: list[str] = []
    
    @rx.var
    def formatted_skills(self) -> str:
        """Get skills as a comma-separated string."""
        return ",".join(self.skills) if self.skills else ""

    @rx.var
    def formatted_projects(self) -> str:
        """Get projects as a comma-separated string."""
        return ",".join(self.projects) if self.projects else ""
    
    # Online presence links
    linkedin_link: str = ""
    github_link: str = ""
    portfolio_link: str = ""
    
    # Edit mode toggle
    edit_mode: bool = False
    show_edit_form: bool = False

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
                            f"{self.API_URL}/profiles/{self.profile_username}/",
                            headers=headers,
                            follow_redirects=True
                        )
                        
                        print(f"Profile API Response: {response.status_code}")
                        
                        if response.status_code == 200:
                            # Process the response data
                            data = response.json()
                            print(f"Received profile data: {data}")
                            
                            # Update basic info - handle null values properly
                            self.first_name = data.get("first_name") or ""
                            self.last_name = data.get("last_name") or ""
                            self.name = f"{self.first_name} {self.last_name}".strip() or "No Name"
                            
                            # Handle field name differences
                            self.job_title = data.get("job_title") or "No Job Title"
                            self.experience_level = data.get("experience_level") or data.get("experience") or "Not Specified"
                            self.category = data.get("category") or data.get("industry") or "Not Specified"
                            self.about = data.get("about") or data.get("bio") or ""
                            
                            # Handle skills - ensure null data shows properly
                            skills_data = data.get("skills") or []
                            if isinstance(skills_data, list):
                                self.skills = skills_data
                            elif isinstance(skills_data, str):
                                # Handle case where skills might be a comma-separated string
                                self.skills = [s.strip() for s in skills_data.split(",") if s.strip()]
                            else:
                                self.skills = []
                            
                            # Handle projects - ensure null data shows properly
                            projects_data = data.get("projects") or []
                            if isinstance(projects_data, list):
                                self.projects = projects_data
                            elif isinstance(projects_data, str):
                                # Handle case where projects might be a comma-separated string
                                self.projects = [p.strip() for p in projects_data.split(",") if p.strip()]
                            else:
                                self.projects = []
                                
                            # Handle social links - ensure null data shows properly
                            # Check for contact_links array first
                            contact_links = data.get("contact_links") or []
                            if contact_links:
                                # Extract links from contact_links array
                                for link in contact_links:
                                    if "linkedin" in link.lower():
                                        self.linkedin_link = link
                                    elif "github" in link.lower():
                                        self.github_link = link
                                    elif "portfolio" in link.lower() or "website" in link.lower():
                                        self.portfolio_link = link
                            else:
                                # Fall back to individual link fields
                                self.linkedin_link = data.get("linkedin_link") or ""
                                self.github_link = data.get("github_link") or ""
                                self.portfolio_link = data.get("portfolio_link") or ""
                        elif response.status_code == 404:
                            # Profile doesn't exist yet, create it
                            print(f"Profile for {self.profile_username} doesn't exist yet. Creating it...")
                            
                            # Get user data from auth debug
                            auth_debug_data = await self.debug_auth_token(auth_token)
                            user_data = auth_debug_data.get("user_from_token", {})
                            
                            # Create a new profile
                            create_response = await client.post(
                                f"{self.API_URL}/profiles/",
                                headers=headers,
                                json={
                                    "username": self.profile_username,
                                    "first_name": user_data.get("first_name", ""),
                                    "last_name": user_data.get("last_name", ""),
                                    "email": user_data.get("email", ""),
                                    "bio": "",
                                    "industry": "Not Specified",
                                    "experience": "Not Specified",
                                    "skills": [],
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
        self.job_title = form_data.get("job_title", self.job_title)
        self.about = form_data.get("about", self.about)
        self.category = form_data.get("category", self.category)
        self.experience_level = form_data.get("experience_level", self.experience_level)
        self.linkedin_link = form_data.get("linkedin_link", self.linkedin_link)
        self.github_link = form_data.get("github_link", self.github_link)
        self.portfolio_link = form_data.get("portfolio_link", self.portfolio_link)
        
        # Update skills from form data
        skills_value = form_data.get("skills", "")
        if skills_value:
            self.skills = [s.strip() for s in skills_value.split(",") if s.strip()]
        
        # Update projects from form data
        projects_value = form_data.get("projects", "")
        if projects_value:
            self.projects = [p.strip() for p in projects_value.split(",") if p.strip()]
        
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
            "username": self.profile_username,  # Include username field
            "first_name": self.first_name,
            "last_name": self.last_name,
            "bio": self.about,  # Map about to bio
            "industry": self.category,  # Map category to industry
            "experience": self.experience_level,  # Map experience_level to experience
            "skills": ",".join(self.skills) if self.skills else "",  # Send skills as a comma-separated string
            "contact_links": [
                {"platform": "linkedin", "url": self.linkedin_link} if self.linkedin_link else None,
                {"platform": "github", "url": self.github_link} if self.github_link else None,
                {"platform": "portfolio", "url": self.portfolio_link} if self.portfolio_link else None
            ]
        }
        
        # Remove None values from contact_links
        profile_data["contact_links"] = [link for link in profile_data["contact_links"] if link is not None]
        
        try:
            # Make the API request directly with httpx
            async with httpx.AsyncClient() as client:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Token {auth_token}"
                }
                
                # Try updating the profile using PUT method
                response = await client.put(
                    f"{self.API_URL}/profiles/{self.profile_username}/",
                    json=profile_data,
                    headers=headers
                )
                
                print(f"Profile update response: {response.status_code}")
                print(f"Profile update response text: {response.text}")
                
                if response.status_code in [200, 201]:
                    print("Profile updated successfully")
                    # Close the form
                    self.show_edit_form = False
                    # Reload profile data to show updates
                    await self.load_profile_data()
                elif response.status_code == 401:
                    print("Authentication error when saving profile")
                    # Handle auth errors
                    return self.handle_auth_error()
                else:
                    print(f"Error updating profile: {response.text}")
                    # Try updating with a different endpoint
                    try:
                        # Try updating the profile with a different endpoint
                        update_response = await client.put(
                            f"{self.API_URL}/profile/{self.profile_username}/",
                            json=profile_data,
                            headers=headers
                        )
                        
                        print(f"Profile update (alternative) response: {update_response.status_code}")
                        print(f"Profile update (alternative) response text: {update_response.text}")
                        
                        if update_response.status_code in [200, 201]:
                            print("Profile updated successfully with alternative endpoint")
                            # Close the form
                            self.show_edit_form = False
                            # Reload profile data to show updates
                            await self.load_profile_data()
                        else:
                            print(f"Error updating profile with alternative endpoint: {update_response.text}")
                    except Exception as alt_error:
                        print(f"Error with alternative update request: {alt_error}")
        
        except Exception as e:
            print(f"Error saving profile changes: {e}")
        
        # Close the form modal
        self.show_edit_form = False

    def cancel_edit(self):
        """Cancel editing."""
        self.show_edit_form = False

    @rx.var
    def has_about(self) -> bool:
        """Check if about text exists."""
        return len(self.about) > 0

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
                    rx.heading(State.name, size="7", class_name="text-sky-600 font-bold"),
                    rx.hstack(
                        rx.text(f"Job: {State.job_title}"),
                        align_items="center",
                        spacing="2"
                    ),
                    rx.hstack(
                        rx.badge(
                            State.category,
                            class_name="bg-blue-100 text-blue-800 px-3 py-1 rounded-full"
                        ),
                        rx.badge(
                            State.experience_level,
                            class_name="bg-green-100 text-green-800 px-3 py-1 rounded-full"
                        ),
                        spacing="2"
                    ),
                    align_items="start",
                    spacing="2"
                ),
                rx.spacer(),
                # Edit Profile Button
                rx.button(
                    rx.icon("pencil"),  # This is the pencil icon
                    on_click=State.toggle_edit_form,
                    class_name="px-6 py-3 bg-white text-gray-600 rounded-lg hover:bg-sky-200 hover:text-gray-600 transition-all duration-200"),
                width="100%",
                padding="4",
                spacing="4"
            ),
            
            # About Section
            rx.box(
                rx.heading("About", size="5", margin_bottom="2"),
                rx.cond(
                    State.has_about,
                    rx.text(State.about),
                    rx.text("No description provided.", class_name="text-gray-500 italic")
                ),
                width="100%",
                padding="4",
                class_name="bg-white rounded-lg shadow"
            ),
            
            # Skills Section
            rx.box(
                rx.hstack(
                    rx.heading("Skills", size="5"),
                    rx.spacer(),
                    width="100%",
                    margin_bottom="2",
                ),
                rx.flex(
                    rx.foreach(
                        State.skills,
                        skill_badge
                    ),
                    wrap="wrap",
                    gap="2"
                ),
                width="100%",
                padding="4",
                class_name="bg-white rounded-lg shadow"
            ),
            
            # Projects Section
            rx.box(
                rx.hstack(
                    rx.heading("Projects", size="5"),
                    rx.spacer(),
                    width="100%",
                    margin_bottom="2",
                ),
                rx.cond(
                    State.projects.length() > 0,
                    rx.flex(
                        rx.foreach(
                            State.projects,
                            project_badge
                        ),
                        wrap="wrap",
                        gap="2"
                    ),
                    rx.text("No projects added yet.", class_name="text-gray-500 italic")
                ),
                width="100%",
                padding="4",
                class_name="bg-white rounded-lg shadow"
            ),
            
            # Online Presence Section
            rx.box(
                rx.heading("Online Presence", size="5", margin_bottom="2"),
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
            
            width="100%",
            max_width="1000px",
            margin="auto",
            padding="4",
            spacing="4"
        ),
        class_name="bg-white rounded-lg shadow-lg p-6 w-full max-w-6xl mx-auto"
    )

def edit_form() -> rx.Component:
    """Render the edit form as a modal dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                "Edit Profile", 
                class_name="text-3xl font-bold mb-4 text-blue-600",
            ),
            rx.dialog.description(
                rx.form(
                    rx.vstack(
                        # Profile Photo Upload
                        rx.vstack(
                            rx.box(
                                rx.cond(
                                    AuthState.profile_picture,
                                    rx.image(
                                        src=AuthState.profile_picture,
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
                            rx.button(
                                rx.hstack(
                                    rx.icon("plus", size=16),
                                    rx.text("Upload profile photo"),
                                    spacing="1"
                                ),
                                class_name="px-4 py-2 bg-gray-200 text-gray-700 hover:bg-gray-300 rounded-lg mt-2",
                            ),
                            align="center",
                            spacing="2",
                            margin_bottom="6"
                        ),
                        
                        # Name Fields
                        rx.hstack(
                            rx.vstack(
                                rx.text("First Name", font_weight="medium", align="left", width="100%"),
                                rx.input(
                                    placeholder="First Name",
                                    name="first_name",
                                    required=True,
                                    value=State.first_name,
                                    on_change=State.set_first_name,
                                    class_name="w-full p-2 border rounded-lg bg-white",
                                ),
                                width="100%",
                                align_items="start"
                            ),
                            rx.vstack(
                                rx.text("Last Name", font_weight="medium", align="left", width="100%"),
                                rx.input(
                                    placeholder="Last Name",
                                    name="last_name",
                                    required=True,
                                    value=State.last_name,
                                    on_change=State.set_last_name,
                                    class_name="w-full p-2 border rounded-lg bg-white",
                                ),
                                width="100%",
                                align_items="start"
                            ),
                            width="100%",
                            spacing="4"
                        ),
                        
                        # Job Title Field
                        rx.text("Job Title", font_weight="medium", align="left", width="100%"),
                        rx.input(
                            placeholder="Your job title",
                            name="job_title",
                            value=State.job_title,
                            on_change=State.set_job_title,
                            class_name="w-full p-2 border rounded-lg bg-white",
                        ),
                        
                        # Industry & Experience
                        rx.hstack(
                            rx.vstack(
                                rx.text("Industry", font_weight="medium", align="left", width="100%"),
                                rx.select(
                                    ["Technology", "Finance", "Healthcare", "Education", "E-commerce", "Other"],
                                    placeholder="Select industry",
                                    name="category",
                                    value=State.category,
                                    on_change=State.set_category,
                                    class_name="w-full p-2 border rounded-lg bg-white",
                                ),
                                width="100%",
                                align_items="start"
                            ),
                            rx.vstack(
                                rx.text("Years of Experience", font_weight="medium", align="left", width="100%"),
                                rx.select(
                                    ["< 1 year", "1-3 years", "3-5 years", "5-10 years", "10+ years"],
                                    placeholder="Select experience",
                                    name="experience_level",
                                    value=State.experience_level,
                                    on_change=State.set_experience_level,
                                    class_name="w-full p-2 border rounded-lg bg-white",
                                ),
                                width="100%",
                                align_items="start"
                            ),
                            width="100%",
                            spacing="4"
                        ),
                        
                        # About Section
                        rx.text("About", font_weight="medium", align="left", width="100%"),
                        rx.text_area(
                            placeholder="Tell us about yourself...",
                            name="about",
                            value=State.about,
                            on_change=State.set_about,
                            height="120px",
                            class_name="w-full p-2 border rounded-lg bg-white",
                        ),
                        
                        # Skills Section
                        rx.text("Skills", font_weight="medium", align="left", width="100%", margin_top="4"),
                        rx.input(
                            placeholder="Skills (comma-separated)",
                            name="skills",
                            value=State.formatted_skills,
                            on_change=lambda value: State.set_skills(value.split(",")),
                            class_name="w-full p-2 border rounded-lg bg-white",
                        ),
                        
                        # Projects Section
                        rx.text("Projects", font_weight="medium", align="left", width="100%", margin_top="4"),
                        rx.input(
                            placeholder="Projects (comma-separated)",
                            name="projects",
                            value=State.formatted_projects,
                            on_change=lambda value: State.set_projects(value.split(",")),
                            class_name="w-full p-2 border rounded-lg bg-white",
                        ),
                        
                        # Online Presence
                        rx.text("Online Presence", font_weight="medium", align="left", width="100%", margin_top="4"),
                        rx.hstack(
                            rx.icon("linkedin", color="blue.500"),
                            rx.input(
                                placeholder="LinkedIn URL",
                                name="linkedin_link",
                                value=State.linkedin_link,
                                on_change=State.set_linkedin_link,
                                class_name="w-full p-2 border rounded-lg bg-white",
                            ),
                            width="100%"
                        ),
                        rx.hstack(
                            rx.icon("github", color="gray.800"),
                            rx.input(
                                placeholder="GitHub URL",
                                name="github_link",
                                value=State.github_link,
                                on_change=State.set_github_link,
                                class_name="w-full p-2 border rounded-lg bg-white",
                            ),
                            width="100%"
                        ),
                        rx.hstack(
                            rx.icon("globe", color="green.500"),
                            rx.input(
                                placeholder="Portfolio Website",
                                name="portfolio_link",
                                value=State.portfolio_link,
                                on_change=State.set_portfolio_link,
                                class_name="w-full p-2 border rounded-lg bg-white",
                            ),
                            width="100%"
                        ),
                        
                        # Buttons
                        rx.hstack(
                            rx.dialog.close(
                                rx.button(
                                    "Cancel",
                                    class_name="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg",
                                ),
                            ),
                            rx.dialog.close(
                                rx.button(
                                    "Save Profile",
                                    type="submit",
                                    class_name="px-6 py-2 bg-sky-600 text-white hover:bg-sky-700 rounded-lg",
                                ),
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
                        State.name,
                        size="4",
                        color="white",
                        class_name="mb-4"
                    ),
                    rx.spacer(),
                    # Add logout button
                    rx.button(
                        "Log Out",
                        on_click=State.logout,
                        class_name="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                    ),
                    width="100%",
                ),
                
                # Auth Debug Information (displayed at top for easy access)
                rx.box(
                    rx.heading("Auth Debug Info", size="6", margin_bottom="2", color="white"),
                    rx.text(State.auth_debug_result, color="white"),
                    # Replace direct DOM manipulation with on_mount event handler
                    rx.html(
                        "",
                        id="token-display",
                        tag="p", 
                        color="white",
                    ),
                    width="100%",
                    padding="4",
                    class_name="bg-gray-800 rounded-lg mb-4"
                ),
                
                # Profile content
                profile_display(),
                
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