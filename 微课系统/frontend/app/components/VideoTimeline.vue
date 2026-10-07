<template>
  <section v-if="videoUrl && timeline?.length" class="ecard player-card">
    <header class="ecard__head">
      <h2 class="ecard__title">
        <span class="ecard__index">05</span>
        <span>视频回放与分析时间轴</span>
      </h2>
      <span class="ecard__hint">Video Replay · Gesture Timeline</span>
    </header>

    <div class="player-body">
      <!-- 视频播放器 -->
      <video
        ref="videoPlayer"
        :src="videoUrl"
        class="video-player"
        controls
        aria-label="教学视频回放"
        @timeupdate="onTimeUpdate"
        @loadedmetadata="onVideoLoaded"
      />

      <!-- 播放位置扫描线 -->
      <ScanLineProgress :percent="duration ? (currentTime / duration) * 100 : 0" :active="false" />

      <!-- 时间轴容器 -->
      <div class="timeline-container">
        <!-- 手势标记行 -->
        <div class="timeline-gestures" ref="gestureTrack">
          <div
            v-for="(seg, idx) in timeline"
            :key="'g-' + idx"
            class="gesture-dot"
            :class="{ active: seg.gesture > 0 }"
            :style="segmentStyle(seg)"
            :title="gestureTitle(seg)"
          />
        </div>

        <!-- 时间轴主轨道 -->
        <div
          class="timeline-track"
          ref="timelineTrack"
          role="slider"
          :aria-label="`播放进度 ${formatTime(currentTime)} / ${formatTime(videoDuration)}`"
          :aria-valuenow="Math.round(currentTime)"
          :aria-valuemin="0"
          :aria-valuemax="Math.round(videoDuration)"
          tabindex="0"
          @click="seekTo"
          @keydown.left.prevent="seekRelative(-5)"
          @keydown.right.prevent="seekRelative(5)"
        >
          <div
            v-for="(seg, idx) in timeline"
            :key="idx"
            class="timeline-segment"
            :class="{ 'is-back': seg.back, 'is-current': currentSegIdx === idx }"
            :style="segmentStyle(seg)"
            :title="seg.text"
            @mouseenter="hoveredSeg = seg"
            @mouseleave="hoveredSeg = null"
          />
          <div class="timeline-cursor" :style="{ left: cursorLeft + '%' }">
            <span class="timeline-cursor__handle" aria-hidden="true" />
          </div>
        </div>

        <!-- 时间刻度 -->
        <div class="timeline-ticks">
          <span
            v-for="tick in timeTicks"
            :key="tick.t"
            class="tick"
            :style="{ left: tick.pct + '%' }"
          >{{ tick.label }}</span>
        </div>

        <!-- 悬浮文字预览 -->
        <div v-if="hoveredSeg" class="timeline-tooltip" aria-live="polite">
          <span v-if="hoveredSeg.back" class="tooltip-tag tooltip-back">背对</span>
          <span v-if="hoveredSeg.gesture > 0" class="tooltip-tag tooltip-gesture">手势 ×{{ hoveredSeg.gesture }}</span>
          <span class="tooltip-text">{{ hoveredSeg.text }}</span>
          <span class="tooltip-time">{{ formatTime(hoveredSeg.start) }} – {{ formatTime(hoveredSeg.end) }}</span>
        </div>
      </div>

      <!-- 图例 -->
      <div class="timeline-legend">
        <span class="legend-item">
          <span class="legend-swatch normal" aria-hidden="true" /> 正常
        </span>
        <span class="legend-item">
          <span class="legend-swatch back" aria-hidden="true" /> 背对学生
        </span>
        <span class="legend-item">
          <span class="legend-swatch gesture" aria-hidden="true" /> 手势
        </span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { TimelineSegment } from '~/types'

const props = defineProps<{
  videoUrl: string
  timeline: TimelineSegment[]
  duration: number
}>()

// --- Refs ---
const videoPlayer = ref<HTMLVideoElement>()
const timelineTrack = ref<HTMLElement>()
const currentTime = ref(0)
const videoDuration = ref(0)
const hoveredSeg = ref<TimelineSegment | null>(null)
const currentSegIdx = ref(-1)

// --- Video events ---
const onVideoLoaded = () => {
  if (videoPlayer.value) {
    videoDuration.value = videoPlayer.value.duration
  }
}

const onTimeUpdate = () => {
  if (videoPlayer.value) {
    currentTime.value = videoPlayer.value.currentTime
    currentSegIdx.value = props.timeline.findIndex(
      (seg) => currentTime.value >= seg.start && currentTime.value < seg.end
    )
  }
}

// --- Timeline positioning ---
const segmentStyle = (seg: TimelineSegment) => {
  const duration = videoDuration.value || props.duration || 1
  const left = (seg.start / duration) * 100
  const width = Math.max(((seg.end - seg.start) / duration) * 100, 0.5)
  return { left: left + '%', width: width + '%' }
}

const cursorLeft = computed(() => {
  const duration = videoDuration.value || 1
  return (currentTime.value / duration) * 100
})

// --- Time ticks ---
const timeTicks = computed(() => {
  const duration = videoDuration.value || props.duration || 60
  const ticks = []
  const interval = duration <= 60 ? 10 : duration <= 180 ? 30 : 60
  for (let t = 0; t <= duration; t += interval) {
    ticks.push({ t, pct: (t / duration) * 100, label: formatTime(t) })
  }
  return ticks
})

// --- Helpers ---
const formatTime = (seconds: number): string => {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

const gestureTitle = (seg: TimelineSegment): string => {
  if (seg.gesture > 0) return seg.gesture + ' 次手势 · ' + seg.text
  return seg.text
}

// --- Seek ---
const seekTo = (e: MouseEvent) => {
  if (!timelineTrack.value || !videoPlayer.value) return
  const rect = timelineTrack.value.getBoundingClientRect()
  const pct = (e.clientX - rect.left) / rect.width
  videoPlayer.value.currentTime = pct * videoDuration.value
}

const seekRelative = (deltaSec: number) => {
  if (!videoPlayer.value) return
  videoPlayer.value.currentTime = Math.max(0, Math.min(videoDuration.value, videoPlayer.value.currentTime + deltaSec))
}
</script>

<style scoped>
.player-card {
  animation: fade-in-up 400ms var(--ease-editorial) both;
  animation-delay: 50ms;
}

.ecard__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}

.ecard__title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
  color: var(--fg);
  font-weight: var(--font-normal);
  margin: 0;
}

.ecard__index {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-wide);
  color: var(--muted);
  border: 1px solid var(--border);
  padding: 2px 6px;
  line-height: 1;
}

.ecard__hint {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-wide);
  color: var(--muted);
  text-transform: uppercase;
}

.player-body {
  display: flex;
  flex-direction: column;
}

/* --- Video player --- */
.video-player {
  width: 100%;
  max-height: 480px;
  display: block;
  background: var(--surface-alt);
  border: 1px solid var(--muted-deep);
  border-bottom: 0;
}

/* --- Timeline container --- */
.timeline-container {
  position: relative;
  padding: var(--space-5) var(--space-6) var(--space-4);
  background: var(--surface-alt);
  border-top: 1px solid var(--border);
}

/* --- Gesture squares --- */
.timeline-gestures {
  position: relative;
  height: 16px;
  margin-bottom: var(--space-2);
}

.gesture-dot {
  position: absolute;
  top: 6px;
  width: 4px;
  height: 4px;
  background: var(--border);
  transform: translateX(-50%);
  transition: background-color var(--transition-base) var(--ease-editorial);
}

.gesture-dot.active {
  background: var(--primary);
}

/* --- Timeline track --- */
.timeline-track {
  position: relative;
  height: 32px;
  background: var(--surface-alt);
  border: 1px solid var(--border);
  cursor: pointer;
  overflow: hidden;
}

.timeline-track:hover {
  border-color: var(--muted-deep);
}

.timeline-track:focus-visible {
  outline: 1px solid var(--primary);
  outline-offset: 2px;
}

.timeline-segment {
  position: absolute;
  top: 0;
  height: 100%;
  background: var(--border);
  border-right: 1px solid var(--bg);
  transition: background-color var(--transition-base) var(--ease-editorial);
}

.timeline-segment.is-back {
  background-color: rgba(156, 59, 48, 0.55);
  background-image: repeating-linear-gradient(
    45deg,
    transparent 0,
    transparent 4px,
    rgba(156, 59, 48, 0.35) 4px,
    rgba(156, 59, 48, 0.35) 8px
  );
}

.timeline-segment.is-current {
  background: var(--primary);
  outline: 1px solid var(--primary);
  outline-offset: -1px;
  z-index: 2;
}

/* --- Cursor --- */
.timeline-cursor {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--primary);
  z-index: 3;
  pointer-events: none;
  transition: left 0.1s linear;
}

.timeline-cursor__handle {
  position: absolute;
  top: 0;
  left: -3px;
  width: 6px;
  height: 6px;
  background: var(--primary);
}

/* --- Ticks --- */
.timeline-ticks {
  position: relative;
  height: 18px;
  margin-top: var(--space-2);
}

.tick {
  position: absolute;
  transform: translateX(-50%);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.1em;
  color: var(--muted);
  line-height: 1;
}

/* --- Tooltip --- */
.timeline-tooltip {
  margin-top: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--surface);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  min-height: 36px;
  max-width: 360px;
}

.tooltip-tag {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  line-height: 1;
}

.tooltip-back {
  color: var(--color-error);
}

.tooltip-gesture {
  color: var(--primary);
}

.tooltip-text {
  flex: 1;
  min-width: 150px;
  font-size: var(--text-xs);
  color: var(--fg);
}

.tooltip-time {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.1em;
  color: var(--muted);
}

/* --- Legend --- */
.timeline-legend {
  display: flex;
  gap: var(--space-5);
  padding: var(--space-3) var(--space-6) var(--space-4);
  border-top: 1px solid var(--border);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--muted-deep);
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-swatch {
  width: 10px;
  height: 10px;
}

.legend-swatch.normal {
  background: var(--border);
}

.legend-swatch.back {
  background: var(--color-error);
}

.legend-swatch.gesture {
  background: var(--primary);
}

@media (max-width: 640px) {
  .video-player {
    max-height: 280px;
  }

  .timeline-tooltip {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-1);
    max-width: none;
  }

  .tooltip-text {
    min-width: unset;
  }
}
</style>
