/**
 * Call Handler for Startup-HUB
 * This script provides functions for handling WebRTC audio and video calls.
 */

// Global state for call functionality
const callState = {
    ringtoneElement: null,
    titleFlashInterval: null,
    originalTitle: document.title,
    activeRoomCalls: new Map() // Track active calls by room ID
};

/**
 * Handle incoming call notification
 * 
 * @param {Object} data - Call data from WebSocket
 * @param {Object} state - Reflex state object
 */
function handleIncomingCall(data, state) {
    console.log('[WebRTC Debug] Received incoming call notification:', data);
    
    // Get call details
    const caller = data.caller_username;
    const callType = data.call_type || 'audio';
    const invitationId = data.invitation_id || '';
    const roomId = data.room || '';
    const roomName = data.room_name || 'Chat Room';
    
    // Skip if this is our own call
    if (caller === state.username) {
        console.log('[WebRTC Debug] Ignoring our own call notification');
        return;
    }
    
    // Log the call details and state before updating
    console.log(`[WebRTC Debug] Call details - Caller: ${caller}, Type: ${callType}, ID: ${invitationId}, Room: ${roomId}`);
    console.log('[WebRTC Debug] Current state before updating:', {
        show_incoming_call: state.show_incoming_call,
        incoming_caller: state.incoming_caller,
        call_type: state.call_type
    });
    
    // Store call information in activeRoomCalls map
    callState.activeRoomCalls.set(roomId, {
        callerId: data.caller_id || '',
        callerUsername: caller,
        callType: callType,
        invitationId: invitationId,
        startTime: new Date(),
        roomName: roomName
    });
    
    // Check if this is a direct call notification or a room announcement
    const isDirectCall = data.recipient_id === state.user_id || 
                         data.type === 'incoming_call';
    
    if (isDirectCall) {
        // For direct calls - show full incoming call UI with ringtone
        
        // Play ringtone for incoming call
        playRingtone();
        
        // Flash browser title
        startTitleFlashing(caller, callType);
        
        // Show browser notification
        showCallNotification(caller, callType);
        
        // Update state immediately and with a delay as fallback
        // Immediate update
        state.current_chat_user = caller;
        state.call_type = callType;
        state.show_incoming_call = true;
        state.call_invitation_id = invitationId;
        state.incoming_caller = caller;
        
        // Force UI update with delay as fallback (helps with React hydration issues)
        setTimeout(() => {
            state.current_chat_user = caller;
            state.call_type = callType;
            state.show_incoming_call = true; 
            state.call_invitation_id = invitationId;
            state.incoming_caller = caller;
            
            // Log state after update
            console.log('[WebRTC Debug] State updated for incoming call:', {
                show_incoming_call: state.show_incoming_call,
                incoming_caller: state.incoming_caller,
                call_type: state.call_type
            });
            
            // Force reactive update
            if (typeof state._update === 'function') {
                state._update();
            }
        }, 100);
    } else {
        // For room-wide announcements - show a more subtle notification to join
        
        // Show a toast-style notification
        showRoomCallToast(caller, callType, roomName);
        
        // Update state to indicate an active call in the room
        state.active_room_call = {
            room_id: roomId,
            caller: caller,
            call_type: callType,
            invitation_id: invitationId
        };
        
        // Force UI update
        if (typeof state._update === 'function') {
            state._update();
        }
    }
}

/**
 * Show a toast notification for room-wide call announcements
 * 
 * @param {string} caller - Username of call initiator
 * @param {string} callType - Type of call (audio/video)
 * @param {string} roomName - Name of the room where call is happening
 */
function showRoomCallToast(caller, callType, roomName) {
    console.log('[WebRTC Debug] Showing room call toast notification');
    
    // Create toast element if not exists
    if (!document.getElementById('room-call-toast')) {
        const toast = document.createElement('div');
        toast.id = 'room-call-toast';
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: #333;
            color: white;
            padding: 16px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            z-index: 10000;
            display: flex;
            flex-direction: column;
            min-width: 300px;
            font-family: system-ui, -apple-system, sans-serif;
        `;
        
        const header = document.createElement('div');
        header.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        `;
        
        const title = document.createElement('h3');
        title.style.margin = '0';
        title.textContent = 'Active Call';
        
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '&times;';
        closeBtn.style.cssText = `
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
        `;
        closeBtn.onclick = () => {
            document.body.removeChild(toast);
        };
        
        const content = document.createElement('div');
        content.id = 'room-call-toast-content';
        
        const actions = document.createElement('div');
        actions.style.cssText = `
            display: flex;
            justify-content: flex-end;
            margin-top: 12px;
        `;
        
        const joinBtn = document.createElement('button');
        joinBtn.id = 'join-call-btn';
        joinBtn.style.cssText = `
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        `;
        joinBtn.textContent = 'Join Call';
        
        header.appendChild(title);
        header.appendChild(closeBtn);
        actions.appendChild(joinBtn);
        
        toast.appendChild(header);
        toast.appendChild(content);
        toast.appendChild(actions);
        
        document.body.appendChild(toast);
    }
    
    // Update toast content
    const content = document.getElementById('room-call-toast-content');
    if (content) {
        content.innerHTML = `
            <p><strong>${caller}</strong> started a ${callType} call in <strong>${roomName}</strong></p>
        `;
    }
    
    // Update join button action
    const joinBtn = document.getElementById('join-call-btn');
    if (joinBtn) {
        joinBtn.onclick = () => {
            console.log('[WebRTC Debug] User clicked to join call');
            
            // Set state variables to join the call
            if (window.state) {
                window.state.joining_existing_call = true;
                window.state.call_type = callType;
                
                // Call Python event handler to join the call
                window.Reflex.triggerEvent("join_existing_call", {});
                
                // Remove toast
                const toast = document.getElementById('room-call-toast');
                if (toast) {
                    document.body.removeChild(toast);
                }
            }
        };
    }
    
    // Auto-hide after 15 seconds
    setTimeout(() => {
        const toast = document.getElementById('room-call-toast');
        if (toast) {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.5s';
            setTimeout(() => {
                if (toast.parentNode) {
                    document.body.removeChild(toast);
                }
            }, 500);
        }
    }, 15000);
}

/**
 * Play ringtone for incoming call
 */
function playRingtone() {
    console.log('[WebRTC Debug] Attempting to play ringtone');
    
    // Create audio element if not exists
    if (!callState.ringtoneElement) {
        callState.ringtoneElement = new Audio('/static/ringtone.mp3');
        callState.ringtoneElement.loop = true;
        callState.ringtoneElement.volume = 0.7;
        
        // Add error handler
        callState.ringtoneElement.onerror = function(e) {
            console.error('[WebRTC Debug] Ringtone error:', e);
        };
    }
    
    // Try to play with promise handling (modern browsers)
    try {
        const playPromise = callState.ringtoneElement.play();
        
        if (playPromise !== undefined) {
            playPromise
                .then(() => {
                    console.log('[WebRTC Debug] Ringtone playing successfully');
                    // Vibrate device if supported
                    if ('vibrate' in navigator) {
                        navigator.vibrate([500, 200, 500, 200, 500]);
                    }
                })
                .catch(err => {
                    console.warn('[WebRTC Debug] Auto-play prevented:', err);
                    
                    // Setup one-time click handler to play on user interaction
                    const unlockAudio = function() {
                        console.log('[WebRTC Debug] User interaction detected, trying to play ringtone');
                        callState.ringtoneElement.play()
                            .then(() => console.log('[WebRTC Debug] Ringtone playing after user interaction'))
                            .catch(e => console.error('[WebRTC Debug] Still failed to play ringtone:', e));
                            
                        // Remove event listeners after one attempt
                        document.removeEventListener('click', unlockAudio);
                        document.removeEventListener('touchstart', unlockAudio);
                    };
                    
                    // Add event listeners for user interaction
                    document.addEventListener('click', unlockAudio);
                    document.addEventListener('touchstart', unlockAudio);
                });
        }
    } catch (e) {
        console.error('[WebRTC Debug] Exception playing ringtone:', e);
    }
}

/**
 * Check if there's an active call in a room
 * 
 * @param {string} roomId - Room ID to check
 * @returns {Object|null} - Call information or null if no active call
 */
function getActiveCallInRoom(roomId) {
    if (callState.activeRoomCalls.has(roomId)) {
        const callInfo = callState.activeRoomCalls.get(roomId);
        
        // Check if call is still active (less than 2 hours old)
        const now = new Date();
        const callStartTime = callInfo.startTime;
        const callAgeMs = now - callStartTime;
        const twoHoursMs = 2 * 60 * 60 * 1000;
        
        if (callAgeMs < twoHoursMs) {
            return callInfo;
        } else {
            // Call is too old, clean it up
            callState.activeRoomCalls.delete(roomId);
            return null;
        }
    }
    
    return null;
}

/**
 * Stop ringtone
 */
function stopRingtone() {
    console.log('[WebRTC Debug] Stopping ringtone');
    if (callState.ringtoneElement) {
        callState.ringtoneElement.pause();
        callState.ringtoneElement.currentTime = 0;
    }
}

/**
 * Flash the browser title bar
 * 
 * @param {string} caller - Caller's username
 * @param {string} callType - Type of call (audio/video)
 */
function startTitleFlashing(caller, callType) {
    console.log('[WebRTC Debug] Starting title flashing');
    
    // Store original title
    callState.originalTitle = document.title;
    
    // Set up interval to flash title
    callState.titleFlashInterval = setInterval(() => {
        document.title = document.title === callState.originalTitle ?
            `📞 ${callType === 'video' ? 'Video' : 'Audio'} Call from ${caller}` : 
            callState.originalTitle;
    }, 1000);
}

/**
 * Stop flashing the browser title
 */
function stopTitleFlashing() {
    console.log('[WebRTC Debug] Stopping title flashing');
    if (callState.titleFlashInterval) {
        clearInterval(callState.titleFlashInterval);
        callState.titleFlashInterval = null;
        
        // Restore original title
        if (callState.originalTitle) {
            document.title = callState.originalTitle;
        }
    }
}

/**
 * Show browser notification for call
 * 
 * @param {string} caller - Caller's username
 * @param {string} callType - Type of call (audio/video)
 */
function showCallNotification(caller, callType) {
    console.log('[WebRTC Debug] Showing call notification');
    
    if ('Notification' in window) {
        // Check if notification permissions already granted
        if (Notification.permission === 'granted') {
            displayNotification(caller, callType);
        } 
        // Request permission if not denied
        else if (Notification.permission !== 'denied') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    displayNotification(caller, callType);
                }
            });
        }
    }
}

/**
 * Helper to display the notification
 * 
 * @param {string} caller - Caller's username
 * @param {string} callType - Type of call (audio/video)
 */
function displayNotification(caller, callType) {
    const notification = new Notification(`Incoming ${callType === 'video' ? 'Video' : 'Audio'} Call`, {
        body: `${caller} is calling you`,
        icon: '/static/call_icon.svg',
        requireInteraction: true
    });
    
    // Focus window when notification clicked
    notification.onclick = () => {
        window.focus();
        notification.close();
    };
}

/**
 * Clean up call resources
 */
function cleanupCall() {
    console.log('[WebRTC Debug] Cleaning up call resources');
    
    // Stop ringtone
    stopRingtone();
    
    // Stop title flashing
    stopTitleFlashing();
    
    // Remove any active toast notifications
    const toast = document.getElementById('room-call-toast');
    if (toast && toast.parentNode) {
        document.body.removeChild(toast);
    }
}

/**
 * Remove a call from active calls list
 * 
 * @param {string} roomId - Room ID for the call
 */
function removeActiveCall(roomId) {
    console.log('[WebRTC Debug] Removing active call for room:', roomId);
    if (callState.activeRoomCalls.has(roomId)) {
        callState.activeRoomCalls.delete(roomId);
    }
}

// Export functions to global scope
window.callHandler = {
    handleIncomingCall,
    playRingtone,
    stopRingtone,
    startTitleFlashing,
    stopTitleFlashing,
    showCallNotification,
    cleanupCall,
    getActiveCallInRoom,
    removeActiveCall
};

// Initialize call handler when window loads
window.addEventListener('load', function() {
    console.log('[WebRTC Debug] Call handler initialized');
});

// Document exposure check
document.addEventListener('DOMContentLoaded', function() {
    console.log('[WebRTC Debug] DOM content loaded, call handler available:', !!window.callHandler);
});

// Global error handler to catch and log any call-related errors
window.addEventListener('error', function(event) {
    if (event.message && event.message.includes('call')) {
        console.error('[WebRTC Debug] Global error:', event.message, event.error);
    }
}); 
