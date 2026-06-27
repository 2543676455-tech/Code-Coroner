import { FormEvent, useEffect, useState } from "react";
import type { Mode, Report } from "./types";

const API = import.meta.env.VITE_API_URL ?? "";
const stages = [
  "validate_url", "clone_repository", "collect_repository_metadata", "analyze_readme",
  "extract_claims", "analyze_project_structure", "verify_claims",
  "inspect_engineering_quality", "security_scan", "sandbox_test",
  "calculate_scores", "generate_report",
];

function ScoreCard({ label, value, inverse = false }: { label: string; value: number; inverse?: boolean }) {
  const hue = inverse ? 120 - value * 1.2 : value * 1.2;
  return (
    <article className="score-card">
      <div className="score-ring" style={{ "--score": `${value * 3.6}deg`, "--hue": hue } as React.CSSProperties}>
        <strong>{value}</strong><span>/100</span>
      </div>
      <h3>{label}</h3>
    </article>
  );
}

function ReportView({ report }: { report: Report }) {
  const scoreEntries: Array<[string, keyof Report["scores"], boolean?]> = [
    ["README 可信度", "readme_credibility"],
    ["生产可用度", "production_readiness"],
    ["学习价值", "learning_value"],
    ["套壳指数", "wrapper_index", true],
  ];
  const downloadUrl = report.task_id.startsWith("demo-")
    ? `${API}/api/v1/demo/markdown`
    : `${API}/api/v1/audits/${report.task_id}/report/markdown`;
  return (
    <main className="report">
      <section className="hero compact">
        <div><span className="eyebrow">{report.mode === "roast" ? "🔥 毒舌审计" : "专业审计"}</span>
          <h1>{report.repository_metadata.owner}/{report.repository_metadata.name}</h1>
          <p>{report.summary}</p>
        </div>
        <a className="button ghost" href={downloadUrl}>下载 Markdown</a>
      </section>
      {!report.llm_enabled && <div className="notice">LLM 语义核验未启用；当前结果来自确定性规则。</div>}
      <section className="score-grid">
        {scoreEntries.map(([label, key, inverse]) => <ScoreCard key={key} label={label} value={report.scores[key].score} inverse={inverse} />)}
      </section>
      <section className="meta-grid">
        <article className="panel"><span>Python 文件</span><strong>{report.repository_metadata.python_files}</strong></article>
        <article className="panel"><span>Python 行数</span><strong>{report.repository_metadata.lines_of_python}</strong></article>
        <article className="panel"><span>仓库文件</span><strong>{report.repository_metadata.file_count}</strong></article>
        <article className="panel"><span>测试状态</span><strong>{report.test_result.status}</strong></article>
        <article className="panel"><span>默认分支</span><strong>{report.repository_metadata.default_branch || "unknown"}</strong></article>
        <article className="panel"><span>Commit</span><strong>{report.repository_metadata.commit_sha.slice(0, 8) || "unknown"}</strong></article>
      </section>
      <section className="panel section">
        <h2>项目结构</h2>
        <div className="structure-grid">
          <div><span>入口文件</span><strong>{report.project_structure.entrypoints.join(", ") || "未识别"}</strong></div>
          <div><span>包目录</span><strong>{report.project_structure.package_directories.join(", ") || "未识别"}</strong></div>
          <div><span>依赖文件</span><strong>{report.project_structure.dependency_files.join(", ") || "未识别"}</strong></div>
          <div><span>测试文件</span><strong>{report.project_structure.test_files.length}</strong></div>
        </div>
        {report.project_structure.largest_modules.length > 0 && <div className="module-list">
          {report.project_structure.largest_modules.slice(0, 5).map(module =>
            <code key={module.path}>{module.path} · {module.lines} lines</code>)}
        </div>}
        {report.project_structure.architecture_notes.map((note, index) => <p key={index}>• {note}</p>)}
      </section>
      <section className="score-details panel section"><h2>评分依据</h2>
        <div className="two-col">{scoreEntries.map(([label, key]) => <article key={key}>
          <h3>{label}</h3>
          {report.scores[key].additions.map((item, index) => <p className="positive" key={`a-${index}`}>+ {item}</p>)}
          {report.scores[key].deductions.map((item, index) => <p className="negative" key={`d-${index}`}>− {item}</p>)}
        </article>)}</div>
      </section>
      {report.roast && <section className="roast"><span>🔥 证据型吐槽</span><p>{report.roast}</p></section>}
      <section className="panel section"><h2>README 声明核验</h2>
        <div className="list">{report.claims.map(claim => <article className="list-item" key={claim.id}>
          <div><span className={`badge ${claim.status}`}>{claim.status}</span><strong>{claim.claim}</strong></div>
          <p>{claim.reason}</p>
          {claim.evidence.map((evidence, index) => <code key={index}>{evidence.path}:{evidence.line_start ?? 1} · {evidence.excerpt}</code>)}
        </article>)}</div>
      </section>
      <div className="two-col">
        <section className="panel section"><h2>工程质量</h2>{report.engineering_checks.map(check =>
          <div className="check" key={check.id}><span className={`dot ${check.status}`} /><div><strong>{check.name}</strong><p>{check.message}</p></div></div>)}
        </section>
        <section className="panel section"><h2>安全风险</h2>{report.security_findings.length === 0 ? <p>轻量扫描未发现风险。</p> :
          report.security_findings.map(item => <article className="finding" key={`${item.rule_id}-${item.path}-${item.line}`}>
            <span className={`badge ${item.severity}`}>{item.severity}</span><strong>{item.title}</strong>
            <code>{item.path}:{item.line} · {item.excerpt}</code><p>{item.recommendation}</p>
          </article>)}
        </section>
      </div>
      <section className="panel section"><h2>沙箱测试日志</h2><p>{report.test_result.reason}</p><pre>{report.test_result.log || "未生成测试日志"}</pre></section>
    </main>
  );
}

export default function App() {
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState<Mode>("professional");
  const [runTests, setRunTests] = useState(false);
  const [githubToken, setGithubToken] = useState("");
  const [taskId, setTaskId] = useState<string>();
  const [stage, setStage] = useState("");
  const [report, setReport] = useState<Report>();
  const [error, setError] = useState("");

  useEffect(() => {
    if (!taskId || report) return;
    const timer = window.setInterval(async () => {
      const response = await fetch(`${API}/api/v1/audits/${taskId}`);
      if (!response.ok) return;
      const task = await response.json();
      setStage(task.current_stage);
      if (task.status === "completed") {
        const result = await fetch(`${API}/api/v1/audits/${taskId}/report`);
        setReport(await result.json()); window.clearInterval(timer);
      } else if (task.status === "failed") {
        setError(task.error_message ?? "分析失败"); window.clearInterval(timer);
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [taskId, report]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    const response = await fetch(`${API}/api/v1/audits`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repository_url: url,
        mode,
        run_tests: runTests,
        github_token: githubToken || undefined,
      }),
    });
    if (!response.ok) { const body = await response.json(); setError(body.detail ?? "请求失败"); return; }
    setTaskId((await response.json()).task_id); setStage("pending");
  }

  async function demo() {
    setError("");
    const response = await fetch(`${API}/api/v1/demo`);
    if (!response.ok) { setError("无法加载示例报告"); return; }
    setReport(await response.json());
  }

  if (report) return <><nav><button className="brand" onClick={() => { setReport(undefined); setTaskId(undefined); }}>RJ<span>_</span></button><span>RepoJudge</span></nav><ReportView report={report} /></>;
  const progress = Math.max(3, ((stages.indexOf(stage) + 1) / stages.length) * 100);
  return (
    <><nav><div className="brand">RJ<span>_</span></div><span>RepoJudge</span><em>Evidence over promises</em></nav>
      <main className="home"><section className="hero"><div><span className="eyebrow">GitHub 开源项目验尸官</span>
        <h1>不听 README 怎么说，<br /><mark>只看代码能不能跑。</mark></h1>
        <p>输入公开 Python 仓库，RepoJudge 用代码、配置、测试和运行日志逐条核验它的承诺。</p></div></section>
        <section className="audit-box"><form onSubmit={submit}>
          <label>GitHub 仓库地址</label><div className="input-row"><input type="url" required placeholder="https://github.com/owner/repository" value={url} onChange={e => setUrl(e.target.value)} /><button className="button" type="submit">开始分析 →</button></div>
          <div className="options"><div className="segmented"><button type="button" className={mode === "professional" ? "active" : ""} onClick={() => setMode("professional")}>专业模式</button><button type="button" className={mode === "roast" ? "active" : ""} onClick={() => setMode("roast")}>🔥 毒舌模式</button></div>
          <label className="switch"><input type="checkbox" checked={runTests} onChange={e => setRunTests(e.target.checked)} /><span />在 Docker 沙箱中运行测试</label></div>
          <details className="advanced"><summary>可选：GitHub Token</summary>
            <input type="password" autoComplete="off" placeholder="仅用于本次克隆，不保存、不写日志" value={githubToken} onChange={e => setGithubToken(e.target.value)} />
          </details>
        </form>
        {taskId && <div className="progress"><div><span>Agent 正在执行：{stage}</span><b>{Math.round(progress)}%</b></div><i><span style={{ width: `${progress}%` }} /></i></div>}
        {error && <div className="error">{error}</div>}
        <button className="demo-link" onClick={demo}>没有 API Key 或 Docker？查看完整示例报告 →</button></section>
        <section className="feature-grid"><article><b>01</b><h3>声明核验</h3><p>将 README 宣传语转换为可验证规则，证据精确到文件与行号。</p></article><article><b>02</b><h3>工程体检</h3><p>检查测试、部署、配置、日志、异常处理、CI 和类型系统。</p></article><article><b>03</b><h3>安全扫描</h3><p>识别密钥、危险执行、弱配置与常见 Python 安全风险。</p></article></section>
        <aside className="warning">⚠ 分析陌生仓库存在风险。沙箱可降低风险，但不能保证绝对安全；默认不执行目标代码。</aside>
      </main></>
  );
}
