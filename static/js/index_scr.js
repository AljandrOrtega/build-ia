
  const socket = io();
  const videoElement = document.getElementById('videoFeed');
  const statusElement = document.getElementById('cameraStatus');
  const faceCountElement = document.getElementById('faceCount');
  const emotionElement = document.getElementById('emotionResult');
  const recommendationElement = document.getElementById('recommendationResult');
  const startBtn = document.getElementById('startBtn');
  const stopBtn = document.getElementById('stopBtn');

  let localStream = null;
  let analysisInterval = null;

  // Start camera and analysis
  startBtn.addEventListener('click', () => {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        videoElement.srcObject = stream;
        localStream = stream;

        socket.emit('control_camera', { action: 'start' });

        analysisInterval = setInterval(() => {
          const canvas = document.createElement('canvas');
          canvas.width = videoElement.videoWidth;
          canvas.height = videoElement.videoHeight;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
          const imageBase64 = canvas.toDataURL('image/jpeg').split(',')[1];

          socket.emit('analyze_frame', { image: imageBase64 });
        }, 3000);
      })
      .catch(err => {
        console.error("Error accessing webcam:", err);
        statusElement.textContent = `Error: ${err.message}`;
        statusElement.className = 'inline-block px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800';
      });
  });

  // Stop camera and analysis
  stopBtn.addEventListener('click', () => {
    socket.emit('control_camera', { action: 'stop' });

    if (localStream) {
      localStream.getTracks().forEach(track => track.stop());
      videoElement.srcObject = null;
      localStream = null;
    }

    clearInterval(analysisInterval);

    // Reset UI
    statusElement.textContent = 'Camera Inactive';
    statusElement.className = 'inline-block px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800';
    faceCountElement.textContent = '0';
    emotionElement.textContent = '-';
    recommendationElement.innerHTML = '<p class="text-gray-500 italic">Analysis results will appear here</p>';
  });

  // Receive analysis results
  socket.on('camera_update', (data) => {
    faceCountElement.textContent = data.faces;
    emotionElement.textContent = data.emotion;

    if (data.recommendation) {
      recommendationElement.innerHTML = `
        <div class="flex items-start">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-green-500 mr-2 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p class="font-medium text-gray-800">${data.recommendation}</p>
            ${data.faces > 0 ? '<p class="text-sm text-gray-600 mt-2">Analysis updates every 3 seconds</p>' : ''}
          </div>
        </div>
      `;
    }
  });

  // Handle camera status from backend
  socket.on('camera_status', (data) => {
    statusElement.textContent = `Camera ${data.status === 'active' ? 'Active' : 'Inactive'}`;
    statusElement.className = `inline-block px-3 py-1 rounded-full text-sm font-medium ${data.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`;
    stopBtn.disabled = data.status !== 'active';
    startBtn.disabled = data.status === 'active';
  });

  // Handle backend errors
  socket.on('camera_error', (data) => {
    statusElement.textContent = `Error: ${data.message}`;
    statusElement.className = 'inline-block px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800';
    recommendationElement.innerHTML = `<p class="text-red-600">${data.message}</p>`;
  });