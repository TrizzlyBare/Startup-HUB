import reflex as rx


class VideoCallState(rx.State):
    local_stream: str = ""
    remote_streams: list = []
    error: str = ""

    def start_call(self):
        return rx.call_script(
            """
            async function startCall() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                    document.getElementById('localVideo').srcObject = stream;
                    
                    // Store stream for cleanup
                    window.localStream = stream;
                    
                    // Setup peer connections for each user
                    const peerConnections = {};
                    otherUsers.forEach(user => {
                        const peerConnection = new RTCPeerConnection();
                        peerConnections[user.id] = peerConnection;
                        
                        peerConnection.ontrack = event => {
                            const videoEl = document.createElement('video');
                            videoEl.srcObject = event.streams[0];
                            videoEl.autoplay = true;
                            videoEl.className = 'remote-video';
                            document.getElementById('remoteVideos').appendChild(videoEl);
                        };
                        
                        stream.getTracks().forEach(track => 
                            peerConnection.addTrack(track, stream));
                    });
                    
                } catch (error) {
                    console.error('Error accessing media devices:', error);
                    window.setError('Failed to access camera and microphone. Please check your settings.');
                }
            }
            startCall();
        """
        )

    def cleanup(self):
        return rx.call_script(
            """
            if (window.localStream) {
                window.localStream.getTracks().forEach(track => track.stop());
            }
        """
        )

    def set_error(self, error: str):
        self.error = error


def video_call():
    return rx.box(
        rx.grid(
            rx.box(
                rx.video(
                    id="localVideo",
                    auto_play=True,
                    muted=True,
                    background_color="black",
                ),
            ),
            rx.box(
                id="remoteVideos",
                background_color="black",
            ),
            rx.cond(
                VideoCallState.error != "",
                rx.alert(
                    rx.alert_title("Error"),
                    rx.alert_description(VideoCallState.error),
                    status="error",
                ),
            ),
            template_columns="repeat(2, 1fr)",
            gap="4",
            width="100%",
            height="100%",
        ),
        on_mount=VideoCallState.start_call,
        on_unmount=VideoCallState.cleanup,
    )


app = rx.App(state=VideoCallState)
app.add_page(video_call)
