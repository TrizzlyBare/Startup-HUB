/**
 * Call Handler for Startup-HUB
 * This script provides functions for handling WebRTC audio and video calls.
 */

// Global state for call functionality
const callState = {
    ringtoneElement: null,
    titleFlashInterval: null,
    originalTitle: document.title
};

/**
 * Handle incoming call notification
 * 
 * @param {Object} data - Call data from WebSocket
 * @param {Object} state - Reflex state object
 */
function handleIncomingCall(data, state) {
    console.log('Incoming call received:', data);
    
    // Get call details
    const caller = data.caller_username;
    const callType = data.call_type || 'audio';
    const invitationId = data.invitation_id || '';
    
    // Update state asynchronously
    setTimeout(() => {
        // Show incoming call notification
        state.current_chat_user = caller;
        state.call_type = callType;
        state.show_incoming_call = true;
        state.call_invitation_id = invitationId;
        state.incoming_caller = caller;
        
        // Play ringtone
        playRingtone();
        
        // Flash title to get user attention
        startTitleFlashing(caller, callType);
        
        // Show browser notification if possible
        showCallNotification(caller, callType);
        
        // Force UI update
        state = {...state};
        console.log('Call notification state updated', {
            show_incoming_call: state.show_incoming_call,
            incoming_caller: state.incoming_caller,
            call_type: state.call_type
        });
    }, 0);
}

/**
 * Play ringtone for incoming call
 */
function playRingtone() {
    // Create audio element for ringtone if it doesn't exist
    if (!callState.ringtoneElement) {
        callState.ringtoneElement = new Audio('/static/ringtone.mp3');
        callState.ringtoneElement.loop = true;
    }
    
    // Play ringtone
    try {
        const playPromise = callState.ringtoneElement.play();
        
        // Handle browsers that return a promise from play()
        if (playPromise !== undefined) {
            playPromise.catch(error => {
                console.log('Error playing ringtone:', error);
                
                // Add click handler to unlock audio on user interaction
                const unlockAudio = () => {
                    callState.ringtoneElement.play();
                    document.removeEventListener('click', unlockAudio);
                    document.removeEventListener('touchstart', unlockAudio);
                };
                document.addEventListener('click', unlockAudio);
                document.addEventListener('touchstart', unlockAudio);
            });
        }
    } catch(e) {
        console.log('Exception playing ringtone:', e);
    }
}

/**
 * Stop ringtone
 */
function stopRingtone() {
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
    callState.originalTitle = document.title;
    
    callState.titleFlashInterval = setInterval(() => {
        const callTypeLabel = callType === 'video' ? 'Video' : 'Audio';
        document.title = document.title.includes('Call') ? 
            callState.originalTitle : `📞 Incoming ${callTypeLabel} Call from ${caller}`;
    }, 1000);
}

/**
 * Stop flashing the browser title
 */
function stopTitleFlashing() {
    if (callState.titleFlashInterval) {
        clearInterval(callState.titleFlashInterval);
        document.title = callState.originalTitle;
    }
}

/**
 * Show browser notification for call
 * 
 * @param {string} caller - Caller's username
 * @param {string} callType - Type of call (audio/video)
 */
function showCallNotification(caller, callType) {
    if ('Notification' in window && Notification.permission === 'granted') {
        const callTypeLabel = callType === 'video' ? 'Video' : 'Audio';
        const notification = new Notification(`Incoming ${callTypeLabel} Call`, {
            body: `${caller} is calling you`,
            icon: '/static/call_icon.png',
            requireInteraction: true
        });
        
        // Handle notification click
        notification.onclick = () => {
            window.focus();
            notification.close();
        };
    } else if ('Notification' in window && Notification.permission !== 'denied') {
        Notification.requestPermission();
    }
}

/**
 * Clean up call resources
 */
function cleanupCall() {
    stopRingtone();
    stopTitleFlashing();
}

// Export functions to global scope
window.callHandler = {
    handleIncomingCall,
    playRingtone,
    stopRingtone,
    startTitleFlashing,
    stopTitleFlashing,
    showCallNotification,
    cleanupCall
}; 