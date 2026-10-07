// ==========================================================================
// 学思践悟 — Report Export Composable
// ==========================================================================
import type { AnalysisResult } from '~/types'

/**
 * 生成分析报告 HTML 字符串
 */
function buildReportHTML(result: AnalysisResult): string {
  const now = new Date().toLocaleString('zh-CN')
  const alerts = result.vision_analysis?.alerts || []
  const standards = result.referenced_standards || []
  const feedback = (result.socratic_feedback || '').replace(/\n/g, '<br>')
  const transcription = (result.transcription || '（无语音内容）').replace(/\n/g, '<br>')
  const va = result.vision_analysis

  const alertRows = alerts
    .map(
      (a) => {
        const colors: Record<string, { bg: string; text: string; border: string }> = {
          error:   { bg: '#FEF2F2', text: '#DC2626', border: '#DC2626' },
          warning: { bg: '#FFFBEB', text: '#D97706', border: '#F59E0B' },
          info:    { bg: '#EFF6FF', text: '#2563EB', border: '#3B82F6' },
          success: { bg: '#F0FDF4', text: '#16A34A', border: '#22C55E' },
        }
        const c = colors[a.level] || colors.info
        return `<div style="padding:8px 12px;margin:4px 0;border-radius:6px;font-size:13px;background:${c.bg};color:${c.text};border-left:3px solid ${c.border}">${a.msg}</div>`
      }
    )
    .join('')

  const standRows = standards
    .map((s) => `<li style="margin:6px 0;font-size:13px;color:#555">${s}</li>`)
    .join('')

  const scores = result.scoring_card || []
  const scoreRows = scores
    .map((s) => {
      const bar = s.score >= 85 ? '#22C55E' : s.score >= 70 ? '#F59E0B' : '#EF4444'
      return `<div style="display:flex;align-items:center;gap:12px;margin:6px 0">
        <span style="font-weight:600;width:80px;font-size:13px">${s.name}</span>
        <div style="flex:1;height:6px;background:#eee;border-radius:3px"><div style="width:${s.score}%;height:100%;background:${bar};border-radius:3px"></div></div>
        <span style="font-weight:700;color:${bar};width:30px;text-align:right">${s.score}</span>
        <span style="font-size:12px;color:#888;width:200px;text-align:right">${s.comment}</span>
      </div>`
    })
    .join('')

  const avg =
    scores.length > 0
      ? Math.round(scores.reduce((sum, s) => sum + s.score, 0) / scores.length)
      : '—'

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>微课教学分析报告</title>
<style>
  body { font-family: 'PingFang SC','Microsoft YaHei',sans-serif; max-width: 800px; margin: 0 auto; padding: 40px 20px; color: #333; line-height: 1.8; }
  .cover { text-align: center; padding: 60px 0; border-bottom: 2px solid #3B82F6; margin-bottom: 40px; }
  .cover h1 { font-size: 28px; color: #1E3A5F; margin-bottom: 12px; }
  .cover .meta { font-size: 14px; color: #888; }
  h2 { font-size: 20px; color: #1E3A5F; border-bottom: 1px solid #E5E7EB; padding-bottom: 8px; margin: 32px 0 16px; }
  .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  .stat-item { background: #F8FAFC; border-radius: 8px; padding: 16px; text-align: center; }
  .stat-value { font-size: 24px; font-weight: 700; color: #3B82F6; }
  .stat-label { font-size: 12px; color: #888; margin-top: 4px; }
  .transcript-block { background: #F8FAFC; padding: 20px; border-radius: 8px; font-size: 14px; }
  .feedback-block { background: #FFF7ED; padding: 20px; border-radius: 8px; border-left: 4px solid #F59E0B; font-size: 14px; }
  .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB; font-size: 12px; color: #999; text-align: center; }
  @media print { body { padding: 20px; } }
</style>
</head>
<body>
<div class="cover">
  <h1>📋 微课教学分析报告</h1>
  <p class="meta">生成时间：${now}　｜　视频时长：${va?.total_duration || '—'} 秒</p>
</div>

<h2>⚡ 教态智能预警</h2>
${alertRows || '<p style="color:#888">无特殊预警</p>'}

${scoreRows ? `<h2>📊 多维评分卡　综合平均：${avg}</h2>${scoreRows}` : ''}

<h2>🎭 教态数据概览</h2>
<div class="stats-grid">
  <div class="stat-item"><div class="stat-value">${va ? (va.back_ratio * 100).toFixed(1) : '—'}%</div><div class="stat-label">背对学生时间</div></div>
  <div class="stat-item"><div class="stat-value">${va?.gesture_intensity || 0}</div><div class="stat-label">手势频次</div></div>
  <div class="stat-item"><div class="stat-value">${va?.gesture_level || '—'}</div><div class="stat-label">手势幅度</div></div>
  <div class="stat-item"><div class="stat-value">${va?.hand_balance || 50}%</div><div class="stat-label">左右均衡度</div></div>
  <div class="stat-item"><div class="stat-value">${va?.is_stiff ? '固定' : '灵活'}</div><div class="stat-label">站位状态</div></div>
  <div class="stat-item"><div class="stat-value">${va?.movement_range || 0}</div><div class="stat-label">位移幅度</div></div>
</div>

<h2>📝 教学语言实录</h2>
<div class="transcript-block">${transcription}</div>

<h2>🤖 AI 苏格拉底式点评</h2>
<div class="feedback-block">${feedback}</div>

<h2>📚 引用课标依据</h2>
<ul>${standRows || '<li style="color:#888">无匹配课标</li>'}</ul>

<div class="footer">本报告由「学思践悟 AI 多模态实训系统」自动生成</div>
</body>
</html>`
}

/**
 * 导出分析报告为 HTML 文件并触发下载
 */
export function useReportExport() {
  const exportReport = (result: AnalysisResult) => {
    if (!result) return

    const html = buildReportHTML(result)
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `微课分析报告_${new Date().toISOString().slice(0, 10)}.html`
    a.click()
    URL.revokeObjectURL(url)
  }

  return { exportReport }
}
