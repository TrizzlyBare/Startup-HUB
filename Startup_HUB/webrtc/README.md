# WebRTC Implementation for Startup-HUB

This module implements WebRTC functionality for Startup-HUB, enabling audio and video calls between users.

## Features

- Audio calls: Make voice calls between users
- Video calls: Make video calls with camera support
- Toggle audio: Mute/unmute during calls
- Toggle video: Enable/disable camera during calls
- Signaling: WebSocket-based signaling for peer connection

## How to Use

### Basic Usage

1. Import the WebRTC components in your page:

```python
from Startup_HUB.webrtc import (
    WebRTCState,
    calling_popup,
    call_popup,
    video_call_popup,
    incoming_call_popup
)
```

2. Add the call popups to your page:

```python
def my_page():
    return rx.box(
        # Your page content
        
        # WebRTC call components
        calling_popup(),
        call_popup(),
        video_call_popup(),
        incoming_call_popup(),
    )
```

3. Implement call buttons:

```python
from Startup_HUB.webrtc import start_audio_call, start_video_call

rx.button(
    "Call",
    on_click=start_audio_call("user123", "John Doe"),
)

rx.button(
    "Video Call",
    on_click=start_video_call("user123", "John Doe"),
)
```

### Custom Call Buttons

You can create custom call buttons using the `create_call_button` function:

```python
from Startup_HUB.webrtc import create_call_button

create_call_button("user123", "John Doe", is_video=False)  # Audio call
create_call_button("user123", "John Doe", is_video=True)   # Video call
```

### Testing

A demo page is available at `/webrtc-demo` to test WebRTC functionality:

1. Open the demo page in two different browsers or tabs
2. Enter different user IDs and usernames
3. Start a call from one browser to another
4. Test the call controls (toggle audio/video, end call)

## Implementation Details

- `webrtc_state.py`: Manages the WebRTC state, connections, and participants
- `webrtc_config.py`: Configuration for WebRTC (STUN servers, media constraints)
- `webrtc_components.py`: UI components for calls (popups, controls)
- `call_utils.py`: Utility functions for initiating and managing calls
- `webrtc_signaling.py`: WebSocket-based signaling implementation
- `static/js/webrtc.js`: JavaScript implementation of WebRTC functionality

## Troubleshooting

1. **Microphone/Camera Access**: Make sure the browser has permission to access the microphone and camera
2. **NAT Traversal**: If calls don't connect, it may be due to NAT/firewall issues. Consider adding TURN servers
3. **Browser Support**: WebRTC is supported in all modern browsers, but check for compatibility

## Future Enhancements

- Screen sharing
- File transfer during calls
- Call recording
- Group calls with more than two participants
- Call quality indicators 