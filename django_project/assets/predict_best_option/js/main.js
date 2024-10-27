// Wait for the DOM to be fully loaded before executing the script
document.addEventListener("DOMContentLoaded", function () {
    const startRecordingButton = document.getElementById("start-recording");
    const stopRecordingButton = document.getElementById("stop-recording");
    const submitAudioButton = document.getElementById("submit-audio");
    const companyDescriptionTextarea = document.getElementById("company_description");
    const audioForm = document.getElementById("audio-form");
    const companyDescriptionInput = document.getElementById("company-description-input");
    const audioInputElement = document.getElementById("audio-file");

    let mediaRecorder;
    let audioChunks = [];
    let audioBlob;

    // Check for browser support and request microphone access
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const source = audioContext.createMediaStreamSource(stream);
            const bufferSize = 4096; // Buffer size
            const scriptProcessor = audioContext.createScriptProcessor(bufferSize, 1, 1);

            // Connect the source to the script processor and start processing
            source.connect(scriptProcessor);
            scriptProcessor.connect(audioContext.destination);

            // Start recording
            startRecordingButton.addEventListener("click", () => {
                audioChunks = [];  // Clear previous chunks
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.start();
                mediaRecorder.ondataavailable = event => {
                    audioChunks.push(event.data);  // Save the audio chunks
                };

                startRecordingButton.disabled = true;
                stopRecordingButton.disabled = false;
            });

            // Stop recording
            stopRecordingButton.addEventListener("click", () => {
                mediaRecorder.stop();
                mediaRecorder.onstop = async () => {
                    audioBlob = new Blob(audioChunks, { type: "audio/wav" });
                    const audioFile = new File([audioBlob], "audio.wav", { type: "audio/wav" });

                    // Assign the audio file to the hidden input field
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(audioFile);
                    audioInputElement.files = dataTransfer.files;

                    // Enable the submit button after recording is stopped
                    submitAudioButton.disabled = false;
                };

                startRecordingButton.disabled = false;
                stopRecordingButton.disabled = true;
            });

            // Event listener to process the audio data in real-time
            scriptProcessor.onaudioprocess = function (event) {
                const inputBuffer = event.inputBuffer.getChannelData(0);
                console.log("Captured audio buffer:", inputBuffer);
                // Process the audio buffer (e.g., analyze it or send it to a server)
            };

        }).catch(err => {
            console.error('Error accessing microphone:', err);
        });

    // Handle form submission
    audioForm.addEventListener('submit', (event) => {
        // Transfer company description to the hidden input before submission
        companyDescriptionInput.value = companyDescriptionTextarea.value;

        // Prevent form submission if company description is empty
        if (companyDescriptionTextarea.value.trim() === '') {
            alert('Please enter a company description.');
            event.preventDefault();
        }
    });
});