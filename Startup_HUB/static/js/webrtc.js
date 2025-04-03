// WebRTC JavaScript implementation
// This file manages WebRTC connections, signaling, and media streams

// Global variables
let localStream = null;
let peerConnections = {};
let roomId = null;
let isCallInitiator = false;
let isAudioEnabled = true;
let isVideoEnabled = false;
let pollingInterval = null;

// Initialize WebRTC
function initializeWebRTC() {
    console.log("Initializing WebRTC...");
    return { success: true };
}

// Connect to the signaling server using polling instead of WebSockets
async function connectToSignalingServer(roomId) {
    if (!roomId) {
        return { success: false, error: "Invalid room ID" };
    }

    try {
        // Join the room
        window.webrtcSignalingState.join_room(roomId, getUserId(), getUserName());
        
        // Start polling for signaling messages
        startPolling();
        
        return { success: true };
    } catch (error) {
        console.error("Error connecting to signaling:", error);
        return { success: false, error: error.message };
    }
}

// Start polling for signaling messages
function startPolling() {
    // Clear any existing polling
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    
    // Poll every second
    pollingInterval = setInterval(async () => {
        try {
            // Check for offers
            const offers = await window.webrtcSignalingState.get_pending_offers();
            if (offers && offers.length > 0) {
                for (const offer of offers) {
                    await handleOffer(offer.sender_id, offer.offer);
                }
            }
            
            // Check for answers
            const answers = await window.webrtcSignalingState.get_pending_answers();
            if (answers && answers.length > 0) {
                for (const answer of answers) {
                    await handleAnswer(answer.sender_id, answer.answer);
                }
            }
            
            // Check for ICE candidates
            const candidates = await window.webrtcSignalingState.get_pending_ice_candidates();
            if (candidates && candidates.length > 0) {
                for (const candidate of candidates) {
                    handleIceCandidate(candidate.sender_id, candidate.candidate);
                }
            }
            
            // Check for participants
            const participants = await window.webrtcSignalingState.get_room_participants(roomId);
            if (participants && participants.length > 0) {
                for (const participant of participants) {
                    if (isCallInitiator && !peerConnections[participant.user_id]) {
                        await startCall(participant.user_id);
                    }
                }
            }
        } catch (error) {
            console.error("Error during polling:", error);
        }
    }, 1000);
}

// Send a message through the signaling system
async function sendSignalingMessage(message) {
    try {
        const { type, sender, receiver, data } = message;
        
        switch (type) {
            case 'offer':
                await window.webrtcSignalingState.send_offer(data, receiver);
                break;
            case 'answer':
                await window.webrtcSignalingState.send_answer(data, receiver);
                break;
            case 'ice-candidate':
                await window.webrtcSignalingState.send_ice_candidate(data, receiver);
                break;
            default:
                console.warn("Unknown message type:", type);
        }
    } catch (error) {
        console.error("Error sending signaling message:", error);
    }
}

// Get the current user ID
function getUserId() {
    // This should be updated to get the actual user ID from the application
    return window.__USER_ID__ || 'unknown';
}

// Get the current username
function getUserName() {
    // This should be updated to get the actual username from the application
    return window.__USER_NAME__ || 'User';
}

// Create a peer connection with a specific user
async function createPeerConnection(userId) {
    const config = {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' },
            { urls: 'stun:stun2.l.google.com:19302' }
        ]
    };

    const pc = new RTCPeerConnection(config);
    peerConnections[userId] = pc;

    // Add local stream tracks to the connection
    if (localStream) {
        localStream.getTracks().forEach(track => {
            pc.addTrack(track, localStream);
        });
    }

    // Handle ICE candidates
    pc.onicecandidate = event => {
        if (event.candidate) {
            sendSignalingMessage({
                type: 'ice-candidate',
                sender: getUserId(),
                receiver: userId,
                data: event.candidate
            });
        }
    };

    // Handle connection state changes
    pc.onconnectionstatechange = event => {
        console.log(`Connection state change: ${pc.connectionState}`);
        if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
            closeConnection(userId);
        }
    };

    // Handle incoming tracks/streams
    pc.ontrack = event => {
        const stream = event.streams[0];
        const videoElement = document.getElementById(`video-${userId}`);
        if (videoElement) {
            videoElement.srcObject = stream;
        }
    };

    return pc;
}

// Handle an incoming offer
async function handleOffer(userId, offer) {
    try {
        // Create a peer connection if it doesn't exist
        const pc = peerConnections[userId] || await createPeerConnection(userId);
        
        // Set the remote description
        await pc.setRemoteDescription(new RTCSessionDescription(offer));
        
        // Get user media if not already acquired
        if (!localStream) {
            await getUserMedia();
        }
        
        // Create an answer
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        
        // Send the answer back
        sendSignalingMessage({
            type: 'answer',
            sender: getUserId(),
            receiver: userId,
            data: answer
        });
    } catch (error) {
        console.error("Error handling offer:", error);
    }
}

// Handle an incoming answer
async function handleAnswer(userId, answer) {
    try {
        const pc = peerConnections[userId];
        if (pc) {
            await pc.setRemoteDescription(new RTCSessionDescription(answer));
        }
    } catch (error) {
        console.error("Error handling answer:", error);
    }
}

// Handle an incoming ICE candidate
function handleIceCandidate(userId, candidate) {
    try {
        const pc = peerConnections[userId];
        if (pc) {
            pc.addIceCandidate(new RTCIceCandidate(candidate));
        }
    } catch (error) {
        console.error("Error handling ICE candidate:", error);
    }
}

// Get user media (microphone/camera)
async function getUserMedia() {
    try {
        const constraints = {
            audio: isAudioEnabled,
            video: isVideoEnabled
        };
        
        localStream = await navigator.mediaDevices.getUserMedia(constraints);
        
        // Display local video if video is enabled
        if (isVideoEnabled) {
            const localVideo = document.getElementById('local-video');
            if (localVideo) {
                localVideo.srcObject = localStream;
            }
        }
        
        return { success: true };
    } catch (error) {
        console.error("Error getting user media:", error);
        return { success: false, error: error.message };
    }
}

// Start a call with a specific user
async function startCall(userId) {
    try {
        // Get user media if not already acquired
        if (!localStream) {
            await getUserMedia();
        }
        
        // Create a peer connection
        const pc = await createPeerConnection(userId);
        
        // Create an offer
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        
        // Send the offer
        sendSignalingMessage({
            type: 'offer',
            sender: getUserId(),
            receiver: userId,
            data: offer
        });
        
        return { success: true };
    } catch (error) {
        console.error("Error starting call:", error);
        return { success: false, error: error.message };
    }
}

// Toggle audio on/off
function toggleAudio(enabled) {
    isAudioEnabled = enabled;
    
    if (localStream) {
        localStream.getAudioTracks().forEach(track => {
            track.enabled = enabled;
        });
    }
    
    return { success: true };
}

// Toggle video on/off
function toggleVideo(enabled) {
    isVideoEnabled = enabled;
    
    if (localStream) {
        localStream.getVideoTracks().forEach(track => {
            track.enabled = enabled;
        });
    }
    
    return { success: true };
}

// Close a specific peer connection
function closeConnection(userId) {
    const pc = peerConnections[userId];
    if (pc) {
        pc.close();
        delete peerConnections[userId];
    }
    
    // Remove video element
    const videoElement = document.getElementById(`video-${userId}`);
    if (videoElement) {
        videoElement.srcObject = null;
    }
}

// Close all connections and clean up
function closeAllConnections() {
    // Stop polling
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
    
    // Close peer connections
    Object.keys(peerConnections).forEach(userId => {
        const pc = peerConnections[userId];
        if (pc) {
            pc.close();
        }
    });
    
    // Clear peer connections
    peerConnections = {};
    
    // Stop local stream
    if (localStream) {
        localStream.getTracks().forEach(track => {
            track.stop();
        });
        localStream = null;
    }
    
    // Clear video elements
    const localVideo = document.getElementById('local-video');
    if (localVideo) {
        localVideo.srcObject = null;
    }
    
    return { success: true };
}

// Expose functions to be called from Python
window.initializeWebRTC = initializeWebRTC;
window.connectToSignalingServer = connectToSignalingServer;
window.startCall = startCall;
window.toggleAudio = toggleAudio;
window.toggleVideo = toggleVideo;
window.closeAllConnections = closeAllConnections; 