class AudioRecorderProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.chunks = [];
        this.totalSamples = 0;
    }

    process(inputs, outputs) {
        const input = inputs[0];
        if (input.length > 0) {
            const samples = input[0];
            if (samples.length > 0) {
                // Convert Float32Array to Int16Array
                const pcmData = new Int16Array(samples.length);
                for (let i = 0; i < samples.length; i++) {
                    const s = Math.max(-1, Math.min(1, samples[i]));
                    pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }
                
                this.chunks.push(pcmData);
                this.totalSamples += pcmData.length;

                // Send chunks every second (16000 samples at 16kHz)
                if (this.totalSamples >= 16000) {
                    const audioData = this.concatenateChunks();
                    this.port.postMessage({ audioData });
                    this.chunks = [];
                    this.totalSamples = 0;
                }
            }
        }
        return true;
    }

    concatenateChunks() {
        const totalLength = this.chunks.reduce((acc, chunk) => acc + chunk.length, 0);
        const result = new Int16Array(totalLength);
        let offset = 0;
        
        for (const chunk of this.chunks) {
            result.set(chunk, offset);
            offset += chunk.length;
        }
        
        return result;
    }
}

registerProcessor('audio-recorder-processor', AudioRecorderProcessor);