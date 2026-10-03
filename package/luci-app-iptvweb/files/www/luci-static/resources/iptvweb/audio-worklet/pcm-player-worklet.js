class IPTVWebPCMPlayer extends AudioWorkletProcessor {
  constructor() {
    super();
    this.channels = 2;
    this.sampleRateHz = sampleRate;
    this.capacityFrames = Math.max(44100, Math.ceil(sampleRate * 2.0));
    this.ring = new Float32Array(this.capacityFrames * this.channels);
    this.readFrame = 0;
    this.writeFrame = 0;
    this.countFrames = 0;
    this.started = false;
    this.startAt = Infinity;
    this.underruns = 0;
    this.overflows = 0;
    this.processedFrames = 0;
    this.lastStatsFrame = 0;
    this.pendingChunks = [];
    this.nextChunkId = 1;

    this.port.onmessage = (event) => {
      const d = event.data || {};
      if (d.type === 'pcm') {
        const input = new Float32Array(d.data);
        const frames = Number(d.samples || Math.floor(input.length / 2));
        if (frames <= 0) return;
        if (frames > this.capacityFrames - this.countFrames) {
          this.overflows++;
          this.port.postMessage({ type: 'overflow', count: this.overflows });
          // Do not drop old audio. Tell the producer to stop sending until the
          // existing ring has drained; the main thread uses its in-flight cap.
          return;
        }
        for (let i = 0; i < frames; i++) {
          const dst = (this.writeFrame + i) % this.capacityFrames;
          this.ring[dst * 2] = input[i * 2] || 0;
          this.ring[dst * 2 + 1] = input[i * 2 + 1] || input[i * 2] || 0;
        }
        this.writeFrame = (this.writeFrame + frames) % this.capacityFrames;
        this.countFrames += frames;
        this.pendingChunks.push({id:Number(d.id||this.nextChunkId++), remaining:frames});
      } else if (d.type === 'start') {
        this.startAt = Number(d.startAt);
        this.started = false;
      } else if (d.type === 'reset') {
        const dropped = this.pendingChunks.length;
        this.pendingChunks = [];
        this.readFrame = 0;
        this.writeFrame = 0;
        this.countFrames = 0;
        this.startAt = Number(d.startAt);
        this.started = false;
        this.port.postMessage({type:'resetAck', dropped});
      } else if (d.type === 'stop') {
        this.started = false;
        this.startAt = Infinity;
        this.readFrame = 0;
        this.writeFrame = 0;
        this.countFrames = 0;
        this.pendingChunks = [];
      } else if (d.type === 'stats') {
        this.sendStats();
      }
    };

    this.port.postMessage({
      type: 'ready',
      sampleRate: this.sampleRateHz,
      capacityFrames: this.capacityFrames
    });
  }

  sendStats() {
    this.port.postMessage({
      type: 'stats',
      queuedSeconds: this.countFrames / this.sampleRateHz,
      underruns: this.underruns,
      overflows: this.overflows,
      started: this.started
    });
  }

  process(inputs, outputs) {
    const output = outputs[0];
    const left = output[0];
    const right = output[1] || output[0];
    const n = left.length;

    if (!this.started && currentTime >= this.startAt) {
      this.started = true;
      this.port.postMessage({ type: 'started', time: currentTime });
    }

    if (!this.started) {
      left.fill(0);
      if (right !== left) right.fill(0);
    } else {
      for (let i = 0; i < n; i++) {
        if (this.countFrames > 0) {
          const src = this.readFrame;
          left[i] = this.ring[src * 2];
          if (right !== left) right[i] = this.ring[src * 2 + 1];
          this.readFrame = (src + 1) % this.capacityFrames;
          this.countFrames--;
          if (this.pendingChunks.length) {
            const chunk=this.pendingChunks[0];
            chunk.remaining--;
            if(chunk.remaining<=0){
              this.pendingChunks.shift();
              this.port.postMessage({type:'ack', id:chunk.id});
            }
          }
        } else {
          left[i] = 0;
          if (right !== left) right[i] = 0;
          this.underruns++;
        }
      }
    }

    this.processedFrames += n;
    if (this.processedFrames - this.lastStatsFrame >= this.sampleRateHz / 4) {
      this.lastStatsFrame = this.processedFrames;
      this.sendStats();
    }
    return true;
  }
}

registerProcessor('iptvweb-pcm-player', IPTVWebPCMPlayer);
