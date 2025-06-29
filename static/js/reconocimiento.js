
// Variable global para el matcher de caras conocidas
let faceMatcher;

// Cargar modelos y caras conocidas antes de iniciar detección
async function iniciar() {
  // Cargar modelos de face-api.js desde la carpeta /models
  await faceapi.nets.tinyFaceDetector.loadFromUri('/models');
  await faceapi.nets.faceLandmark68Net.loadFromUri('/models');
  await faceapi.nets.faceRecognitionNet.loadFromUri('/models');

  // Cargar datos de familiares conocidos (de tu API /familiares)
  const res = await fetch('/familiares');
  const data = await res.json();

  // Mapear datos recibidos a objetos LabeledFaceDescriptors
  const labeledDescriptors = data.map(persona => {
    const descriptors = persona.descriptors.map(d => new Float32Array(d));
    return new faceapi.LabeledFaceDescriptors(persona.label, descriptors);
  });

  faceMatcher = new faceapi.FaceMatcher(labeledDescriptors);

  // Iniciar la detección en video
  detectar();
}

// Función para iniciar la cámara y detectar personas periódicamente
async function detectar() {
  const video = document.getElementById('video');

  // Obtener cámara
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('getUserMedia no es soportado por tu navegador');
    return;
  }

  const stream = await navigator.mediaDevices.getUserMedia({ video: {} });
  video.srcObject = stream;

  // Ejecutar detección cada 3 segundos
  setInterval(async () => {
    // Detectar todas las caras con landmarks y descriptor
    const detections = await faceapi
      .detectAllFaces(video, new faceapi.TinyFaceDetectorOptions())
      .withFaceLandmarks()
      .withFaceDescriptors();

    if (detections.length > 0) {
      // Comparar cada cara detectada con los conocidos
      const resultados = detections.map(det => faceMatcher.findBestMatch(det.descriptor));
      const infoTexto = resultados.map(r => r.toString()).join(', ');
      document.getElementById('info').innerText = `Personas detectadas: ${infoTexto}`;
    } else {
      document.getElementById('info').innerText = 'Nadie conocido identificado';
    }
  }, 3000);
}

// Iniciar todo al cargar la página
window.onload = () => {
  iniciar();
};
