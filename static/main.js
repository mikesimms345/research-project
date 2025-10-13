import io from 'https://cdn.socket.io/4.7.2/socket.io.esm.min.js';

const socket = io();


let localStream;
let remoteStream;
let buf = new BigUint64Array(1);
let room = "room" + crypto.getRandomValues(buf)
let pc;
let mediaRecorder;

const webcamButton = document.getElementById('webcamButton');
const callButton = document.getElementById('callButton');
const copyButton = document.getElementById('copyButton');
const answerButton = document.getElementById('answerButton');
const hangupButton = document.getElementById('hangupButton');
const webcamVideo = document.getElementById('webcamVideo');
const remoteVideo = document.getElementById('remoteVideo');
const logoutButton = document.getElementById('logoutButton');

const servers = {
  iceServers: [
    {
      urls: ['stun:stun1.l.google.com:19302', 'stun:stun2.l.google.com:19302']
    }
  ]
}

// Used so I don't get anymore errors with addTrack
function createPeerConnection() {
  pc = new RTCPeerConnection(servers);

  //Handling Remote Media Stream
  remoteStream = new MediaStream();
  pc.ontrack = event => {
    remoteStream.addTrack(event.track);
    console.log("stream received");
  };
  remoteVideo.srcObject = remoteStream;

  // Ice Candidates
  pc.onicecandidate = event => {
    if (event.candidate) {
      console.log("Sent ICE Candidates");
      socket.emit('ice-candidate', {
        room, candidate: event.candidate
      })
    }
  }
}

// Start webcam
webcamButton.onclick = async () => {
  localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false});
  webcamVideo.srcObject = localStream;
};

// Handling Call Button (For the Caller)
callButton.onclick = async () => {
  if (!localStream) {
    alert("Webcam isn't working, refresh and try again!");
    return;
  }
  createPeerConnection();
  localStream.getTracks().forEach(track => {
    pc.addTrack(track, localStream);
  })
  socket.emit('join', {room});
  console.log("the room id is " + room);
  // Prints the room code to the page
  const para = document.createElement("p");
  const node = document.createTextNode("The Room ID: " + room);
  para.appendChild(node);
  const element = document.getElementById("create_call")
  element.appendChild(para);
}

copyButton.onclick = async () => {
  try {
    await navigator.clipboard.writeText(room);
  } catch (err) {
    console.log("Error: ", err);
  }
  alert("Copied to clipboard");
}

// Handling the answer button (For the Callee)
answerButton.onclick = async () => {
  if (!localStream) {
    alert("Webcam is not on, please refresh the page and try again!");
    return;
  }
  createPeerConnection();
  room = document.getElementById("callInput").value.trim();
  const sanitized_room = room.replace(/[<>]/g, '');
  const element = document.getElementById("error_message");
  if (sanitized_room.length > 24 || sanitized_room.length < 5) {
    element.textContent = "Room ID " + room + " is invalid, try again!";
    return;
  }
  console.log("Sanitized " + sanitized_room);
  if (element) {
    element.textContent = '';
  }

  localStream.getTracks().forEach(track => {
    pc.addTrack(track, localStream);
  });
  console.log("made it here");
  socket.emit ('ans_join', {room});
}

hangupButton.onclick = async () => {
    if (remoteStream) {
        remoteStream.getTracks().forEach(track => track.stop());
    }
    if (pc) {
        pc.close();
        pc = null;
    }
    remoteVideo.srcObject = null;
};


logoutButton.onclick = async () => {
    try {
        const response = await fetch('/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();

        if (response.ok) {
            console.log('Successfully logged out:', data.message);
            window.location.href = '/login';
        } else {
          console.error('Logout failed: ', data.message);
        }
    } catch (error) {
        console.error('An error occurred during the logout process:', error);
    }
};

socket.on('ice-candidate', async (candidate) => {
  if (pc) {
    console.log('Received ice candidate');
    await pc.addIceCandidate(new RTCIceCandidate(candidate));
  }
})

socket.on('joined', async () => {
  if (pc) {
    console.log('Peer has joined, creating offer...');
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    console.log("Local description is set!")
    socket.emit('offer', {room, offer});
  }
})

socket.on('offer', async (offer) => {
  if (!pc){
    createPeerConnection();
  }
  console.log("Received offer");
  await pc.setRemoteDescription(new RTCSessionDescription(offer));
  const answer = await pc.createAnswer();
  await pc.setLocalDescription(answer);
  socket.emit('answer', {room, answer});
})

socket.on('answer', async (answer) => {
  if (pc) {
    console.log("Received answer");
    await pc.setRemoteDescription(new RTCSessionDescription(answer));
  }
})

// Fix this later, want to essentially refresh the remote stream if the other user disconnects
// socket.on('disconnect', () => {
//     socket.emit('disconnect');
//     remoteVideo.removeAttribute('src');
//     remoteVideo.load();
// })

socket.on("failed join", async () => {
  console.log('User failed join');
  const element = document.getElementById("error_message");
  element.textContent = "The room " + room + " does not exist, please try again!";
})