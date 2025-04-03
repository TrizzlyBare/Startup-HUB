import os
import shutil
import reflex as rx

class WebRTCConfig:
    """Configuration for WebRTC functionality."""
    
    # STUN/TURN servers for NAT traversal
    ICE_SERVERS = [
        {"urls": "stun:stun.l.google.com:19302"},
        {"urls": "stun:stun1.l.google.com:19302"},
        {"urls": "stun:stun2.l.google.com:19302"},
    ]
    
    # WebSocket signaling server endpoint
    SIGNALING_URL = "/ws/webrtc/"
    
    # Configuration for the peer connection
    PEER_CONNECTION_CONFIG = {
        "iceServers": ICE_SERVERS,
        "iceTransportPolicy": "all",
        "bundlePolicy": "balanced",
        "rtcpMuxPolicy": "require",
        "sdpSemantics": "unified-plan"
    }
    
    # Media constraints for getUserMedia
    AUDIO_CONSTRAINTS = {
        "echoCancellation": True,
        "noiseSuppression": True,
        "autoGainControl": True
    }
    
    VIDEO_CONSTRAINTS = {
        "width": {"ideal": 1280, "max": 1920},
        "height": {"ideal": 720, "max": 1080},
        "frameRate": {"ideal": 24, "max": 30}
    }

def setup_webrtc_static():
    """Set up WebRTC static files for the application."""
    # Define the source and destination paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    js_source_path = os.path.join(current_dir, "static", "js", "webrtc.js")
    
    # Create the static directory structure if it doesn't exist
    static_dir = os.path.join(os.path.dirname(current_dir), "static", "js")
    os.makedirs(static_dir, exist_ok=True)
    
    # Define the destination path for the WebRTC JavaScript file
    js_dest_path = os.path.join(static_dir, "webrtc.js")
    
    # Create the WebRTC JavaScript file if it doesn't exist
    if not os.path.exists(js_source_path):
        webrtc_js_content = generate_webrtc_js()
        os.makedirs(os.path.dirname(js_source_path), exist_ok=True)
        with open(js_source_path, "w") as f:
            f.write(webrtc_js_content)
    
    # Copy the WebRTC JavaScript file to the static directory if needed
    if not os.path.exists(js_dest_path) or os.path.getmtime(js_source_path) > os.path.getmtime(js_dest_path):
        try:
            shutil.copy2(js_source_path, js_dest_path)
        except Exception as e:
            print(f"Failed to copy WebRTC JavaScript: {e}")
    
    # The script will be added via app.add_head_tags in the main application
    # Instead of directly modifying rx.config.head_components which doesn't exist

def generate_webrtc_js():
    """Generate the WebRTC JavaScript code as a fallback."""
    return """// WebRTC JavaScript implementation
// This file manages WebRTC connections, signaling, and media streams

// Global variables
let localStream = null;
let peerConnections = {};
let roomId = null;
let signalingSocket = null;
let isCallInitiator = false;
let isAudioEnabled = true;
let isVideoEnabled = false;

// Initialize WebRTC
function initializeWebRTC() {
    console.log("Initializing WebRTC...");
    return { success: true };
}

// Connect to the signaling server
async function connectToSignalingServer(url) {
    if (!url) {
        return { success: false, error: "Invalid URL" };
    }

    try {
        // Close existing connection if any
        if (signalingSocket && signalingSocket.readyState !== WebSocket.CLOSED) {
            signalingSocket.close();
        }

        // Create a new WebSocket connection
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}${url}`;
        signalingSocket = new WebSocket(wsUrl);

        signalingSocket.onopen = () => {
            console.log("Connected to signaling server");
        };

        signalingSocket.onmessage = async (event) => {
            const message = JSON.parse(event.data);
            handleSignalingMessage(message);
        };

        signalingSocket.onerror = (error) => {
            console.error("WebSocket error:", error);
        };

        signalingSocket.onclose = () => {
            console.log("Disconnected from signaling server");
        };

        roomId = url.split('/').pop();
        return { success: true };
    } catch (error) {
        console.error("Error connecting to signaling server:", error);
        return { success: false, error: error.message };
    }
}

// Handle incoming signaling messages
async function handleSignalingMessage(message) {
    const { type, sender, data } = message;

    if (sender === getUserId()) {
        return; // Ignore messages from self
    }

    switch (type) {
        case 'offer':
            await handleOffer(sender, data);
            break;
        case 'answer':
            await handleAnswer(sender, data);
            break;
        case 'ice-candidate':
            handleIceCandidate(sender, data);
            break;
        case 'user-joined':
            handleUserJoined(data.userId, data.username);
            break;
        case 'user-left':
            handleUserLeft(data.userId);
            break;
        case 'call-ended':
            closeAllConnections();
            break;
        default:
            console.warn("Unknown message type:", type);
    }
}

// Get the current user ID
function getUserId() {
    // This should be updated to get the actual user ID from the application
    return window.__USER_ID__ || 'unknown';
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

// Handle a user joining the call
function handleUserJoined(userId, username) {
    // Update UI and create a new peer connection
    if (isCallInitiator) {
        // If we're the initiator, send an offer
        startCall(userId);
    }
}

// Handle a user leaving the call
function handleUserLeft(userId) {
    closeConnection(userId);
}

// Send a message through the signaling server
function sendSignalingMessage(message) {
    if (signalingSocket && signalingSocket.readyState === WebSocket.OPEN) {
        signalingSocket.send(JSON.stringify(message));
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
        // Toggle existing video tracks
        localStream.getVideoTracks().forEach(track => {
            track.enabled = enabled;
        });
    } else if (enabled) {
        // Get video stream if not available
        getUserMedia();
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
    // Close all peer connections
    Object.keys(peerConnections).forEach(userId => {
        closeConnection(userId);
    });
    
    // Close local stream
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }
    
    // Close signaling connection
    if (signalingSocket) {
        signalingSocket.close();
        signalingSocket = null;
    }
    
    // Clear room ID
    roomId = null;
    
    return { success: true };
}

// Expose functions to be called from Python
window.initializeWebRTC = initializeWebRTC;
window.connectToSignalingServer = connectToSignalingServer;
window.startCall = startCall;
window.toggleAudio = toggleAudio;
window.toggleVideo = toggleVideo;
window.closeAllConnections = closeAllConnections;
"""

# Call this function when the module is imported 
setup_webrtc_static() 