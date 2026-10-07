<template>
  <div class="scanline" :class="[`scanline--${variant}`, { 'scanline--idle': !active }]" role="progressbar" :aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100">
    <div class="scanline__bar" :style="{ width: `${percent}%` }" />
    <div class="scanline__scan" />
  </div>
</template>

<script setup lang="ts">
/**
 * ScanLineProgress — 技术感扫描线进度条
 * 2px 高容器：左侧为实际进度，上方叠加一条循环移动的扫描亮线
 */
withDefaults(
  defineProps<{
    /** 0-100 的实际进度 */
    percent?: number
    /** 是否处于活动状态（非活动时扫描线减速） */
    active?: boolean
    /** 配色变体 */
    variant?: 'primary' | 'blue'
  }>(),
  {
    percent: 0,
    active: true,
    variant: 'primary',
  }
)
</script>

<style scoped>
.scanline {
  position: relative;
  height: 2px;
  width: 100%;
  background: var(--border);
  overflow: hidden;
}

.scanline__bar {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  background: var(--primary);
  transition: width var(--transition-base) var(--ease-editorial);
}

.scanline__scan {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 40%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(61, 112, 104, 0.55) 45%,
    var(--primary) 50%,
    rgba(61, 112, 104, 0.55) 55%,
    transparent 100%
  );
  animation: scan-line 2s var(--ease-editorial) infinite;
}

.scanline--idle .scanline__scan {
  animation-duration: 3.2s;
}

.scanline--blue .scanline__bar {
  background: #3b82f6;
}

.scanline--blue .scanline__scan {
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(59, 130, 246, 0.5) 45%,
    #3b82f6 50%,
    rgba(59, 130, 246, 0.5) 55%,
    transparent 100%
  );
}

@keyframes scan-line {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(250%); }
}
</style>
