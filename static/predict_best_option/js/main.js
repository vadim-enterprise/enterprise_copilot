// Function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener("DOMContentLoaded", function () {
    // Get CSRF token
    const csrftoken = getCookie('csrftoken');

    const startRecordingButton = document.getElementById("start-recording");
    const stopRecordingButton = document.getElementById("stop-recording");
    const submitAudioButton = document.getElementById("submit-audio");
    const companyDescriptionTextarea = document.getElementById("company_description");
    const audioForm = document.getElementById("audio-form");
    audioForm.addEventListener("submit", submitForm);
    const companyDescriptionInput = document.getElementById("company-description-input");
    let mediaRecorder;
    let audioChunks = [];

    startRecordingButton.addEventListener("click", startRecording);
    stopRecordingButton.addEventListener("click", stopRecording);
    audioForm.addEventListener("submit", submitForm);

    async function startRecording() {
        console.log("Starting recording...");
        audioChunks = [];
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.addEventListener("dataavailable", event => {
                audioChunks.push(event.data);
            });
            mediaRecorder.start();
            startRecordingButton.disabled = true;
            stopRecordingButton.disabled = false;
        } catch (err) {
            console.error("Error accessing the microphone:", err);
            alert("Error accessing the microphone. Please ensure you have given permission to use the microphone.");
        }
    }

    function stopRecording() {
        console.log("Stopping recording...");
        mediaRecorder.stop();
        mediaRecorder.addEventListener("stop", () => {
            startRecordingButton.disabled = false;
            stopRecordingButton.disabled = true;
            submitAudioButton.disabled = false;
        });
    }

    function submitForm(event) {
        console.log("Submit button clicked");
        event.preventDefault();
        console.log("Default form submission prevented");
    
        if (audioChunks.length === 0) {
            console.error("No audio recorded");
            alert("Please record some audio before submitting.");
            return;
        }
    
        const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
        console.log("Audio blob created", audioBlob);
    
        const formData = new FormData(audioForm);
        formData.set("audio_file", audioBlob, "recording.wav");
        formData.set("company_description", companyDescriptionTextarea.value);
        console.log("FormData created", formData);
    
        console.log("Sending fetch request to:", audioForm.action);
        fetch(audioForm.action, {
            method: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            body: formData
        })
        .then(response => {
            console.log("Received response", response);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(html => {
            console.log("Received HTML response");
            document.body.innerHTML = html;
        })
        .catch(error => {
            console.error("Error:", error);
            alert("An error occurred while submitting the form. Please try again.");
        });
    }
});