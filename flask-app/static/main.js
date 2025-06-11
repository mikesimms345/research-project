//import { io } from 'socket.io-client';
import io from 'https://cdn.socket.io/4.7.2/socket.io.esm.min.js';


const socket = io('your signaling server ip address here!');

let localStream;
let remoteStream;
let room = 'webrtc-test-fr';

const webcamButton = document.getElementById('webcamButton');
const callButton = document.getElementById('callButton');
const answerButton = document.getElementById('answerButton');
const hangupButton = document.getElementById('hangupButton');
const webcamVideo = document.getElementById('webcamVideo');
const remoteVideo = document.getElementById('remoteVideo');

const servers = {
  iceServers: [
    {
      urls: ['stun:stun1.l.google.com:19302', 'stun:stun2.l.google.com:19302']
    }
  ]
}

const pc = new RTCPeerConnection(servers);

// Start webcam
webcamButton.onclick = async () => {
  localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
  webcamVideo.srcObject = localStream;
};

//Handling Remote Media Stream
remoteStream = new MediaStream();
pc.ontrack = event => {
  remoteStream.addTrack(event.track);
  console.log("stream received")
};
remoteVideo.srcObject = remoteStream;

// Ice Candidates
pc.onicecandidate = event => {
  if (event.candidate) {
    console.log("Sent ICE Candidates")
    socket.emit('ice-candidate', {
      room, candidate: event.candidate
    })
  }
}

// Handling Call Button
callButton.onclick = async () => {
  socket.emit('join', {room})
  localStream.getTracks().forEach(track => {
    pc.addTrack(track);
  })
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  console.log("local description is set!")

  socket.emit('offer', {room, offer})
}

answerButton.onclick = async () => {
  socket.emit ('join', {room})
  document.querySelector('#callButton').innerHTML = 'Join the Call!'
}

hangupButton.onclick = async () => {
  remoteStream.getTracks().forEach(track => {
    track.stop()
  })
  pc.close();
}

socket.on('ice-candidate', async (candidate) => {
  console.log('Received ice candidate');
  await pc.addIceCandidate(new RTCIceCandidate(candidate));
})

socket.on('joined', () => {
  console.log('User joined');
})

socket.on('offer', async (offer) => {
  console.log("Received offer");

  await pc.setRemoteDescription(new RTCSessionDescription(offer));
  const answer = await pc.createAnswer();
  await pc.setLocalDescription(answer);

  socket.emit('answer', {room, answer})

})

socket.on('answer', async (answer) => {
  console.log("Received answer");
  await pc.setRemoteDescription(new RTCSessionDescription(answer));
})

socket.on('disconnect', () => {
  console.log('User disconnected');
})