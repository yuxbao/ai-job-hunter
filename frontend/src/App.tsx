import {
  ArrowUpRight,
  BriefcaseBusiness,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  Clock3,
  GitCompareArrows,
  GripVertical,
  Layers3,
  Loader2,
  MapPin,
  Radar,
  Search,
  Send,
  Sparkles,
  Star,
  Trash2,
} from "lucide-react";
import { FormEvent, startTransition, useEffect, useMemo, useState } from "react";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./components/ui/collapsible";
import { Input } from "./components/ui/input";
import { Progress } from "./components/ui/progress";
import { ScrollArea } from "./components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { Separator } from "./components/ui/separator";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "./components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Textarea } from "./components/ui/textarea";

type SearchType = "campus" | "intern" | "all";
type JobStatusType = "queued" | "running" | "completed" | "degraded" | "failed";
type WorkspaceLane = "favorites" | "compare" | "applied";

type SearchFormState = {
  job_title: string;
  requirements: string;
  search_type: SearchType;
  cities: string;
  target_count: number;
  exclude_keywords: string;
};

type JobStatusResponse = {
  job_id: string;
  status: JobStatusType;
  stage: string;
  progress: number;
  created_at: string;
  updated_at: string;
  message: string;
  iteration: number;
  counts: Record<string, number>;
  errors: string[];
  recent_events: Array<{ stage: string; message: string; time: string }>;
  summary: Record<string, unknown>;
  request: Record<string, unknown>;
  output_path: string;
};

type JobPosting = {
  title: string;
  company: string;
  location: string;
  salary: string;
  tech_tags: string[];
  requirements: string;
  source: string;
  job_url: string;
  description: string;
  experience_level?: string;
  confidence?: number;
};

type JobResultResponse = JobStatusResponse & {
  result: null | {
    final_jobs: JobPosting[];
    acceptance_passed: boolean;
    acceptance_issues: string[];
    acceptance_summary: Record<string, unknown> & {
      degraded_mode?: boolean;
      warnings?: string[];
    };
    search_warnings?: string[];
    degraded_mode?: boolean;
    sources_used: string[];
    summary_path: string;
    output_path: string;
  };
};

const STAGE_LABELS: Record<string, string> = {
  planner: "需求规划",
  searcher: "多源搜索",
  scraper: "详情抓取",
  quality_gate: "质量门控",
  filter: "岗位筛选",
  enricher: "信息补全",
  evaluator: "结果验收",
  reporter: "结果输出",
};

const INITIAL_FORM: SearchFormState = {
  job_title: "",
  requirements: "",
  search_type: "all",
  cities: "",
  target_count: 30,
  exclude_keywords: "",
};

const WORKSPACE_LANES: Record<
  WorkspaceLane,
  {
    label: string;
    description: string;
    empty: string;
    icon: typeof Star;
  }
> = {
  favorites: {
    label: "收藏",
    description: "先留意，后面集中复盘",
    empty: "把值得继续看的岗位拖到这里",
    icon: Star,
  },
  compare: {
    label: "对比",
    description: "横向比较薪资、地点、匹配度",
    empty: "拖入 2-4 个岗位做取舍",
    icon: GitCompareArrows,
  },
  applied: {
    label: "待投递",
    description: "准备简历、内推和投递动作",
    empty: "最终准备投递的岗位放这里",
    icon: Send,
  },
};

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const contentType = response.headers.get("Content-Type") ?? "";
    const detail = contentType.includes("application/json")
      ? JSON.stringify(await response.json())
      : await response.text();
    const message = detail ? `Request failed: ${response.status} ${detail}` : `Request failed: ${response.status}`;
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function normalizePercent(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value * 100)));
}

function App() {
  const [form, setForm] = useState<SearchFormState>(INITIAL_FORM);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatusResponse | null>(null);
  const [result, setResult] = useState<JobResultResponse | null>(null);
  const [selectedJobUrl, setSelectedJobUrl] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [workspaceJobs, setWorkspaceJobs] = useState<Record<WorkspaceLane, JobPosting[]>>({
    favorites: [],
    compare: [],
    applied: [],
  });

  const jobs = result?.result?.final_jobs ?? [];
  const selectedJob = useMemo(
    () => jobs.find((job) => job.job_url === selectedJobUrl) ?? jobs[0] ?? null,
    [jobs, selectedJobUrl],
  );

  useEffect(() => {
    if (!jobId) {
      return undefined;
    }

    let closed = false;
    const source = new EventSource(`${apiBase}/api/jobs/${jobId}/events`);

    const hydrateResult = async () => {
      try {
        const nextResult = await fetchJson<JobResultResponse>(`/api/jobs/${jobId}/result`);
        if (closed) {
          return;
        }
        startTransition(() => {
          setResult(nextResult);
          setSelectedJobUrl(nextResult.result?.final_jobs[0]?.job_url ?? null);
        });
      } catch (resultError) {
        if (!closed) {
          setError(resultError instanceof Error ? resultError.message : "获取任务结果失败");
        }
      }
    };

    source.addEventListener("status", (event) => {
      const nextStatus = JSON.parse((event as MessageEvent<string>).data) as JobStatusResponse;
      if (closed) {
        return;
      }

      startTransition(() => {
        setStatus(nextStatus);
      });
    });

    source.addEventListener("result", (event) => {
      const nextResult = JSON.parse((event as MessageEvent<string>).data) as JobResultResponse;
      if (closed) {
        return;
      }

      startTransition(() => {
        setStatus(nextResult);
        setResult(nextResult);
        setSelectedJobUrl(nextResult.result?.final_jobs[0]?.job_url ?? null);
      });
      source.close();
    });

    source.onerror = async () => {
      if (closed) {
        return;
      }

      try {
        const fallbackStatus = await fetchJson<JobStatusResponse>(`/api/jobs/${jobId}/status`);
        startTransition(() => {
          setStatus(fallbackStatus);
        });
        if (fallbackStatus.status === "completed" || fallbackStatus.status === "failed") {
          await hydrateResult();
          source.close();
        }
      } catch (pollError) {
        setError(pollError instanceof Error ? pollError.message : "SSE 连接失败");
      }
    };

    return () => {
      closed = true;
      source.close();
    };
  }, [jobId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form.job_title.trim()) {
      setError("请输入岗位名称");
      return;
    }

    setSubmitting(true);
    setError(null);
    setResult(null);
    setStatus(null);
    setSelectedJobUrl(null);
    setDetailOpen(false);

    try {
      const payload = {
        ...form,
        job_title: form.job_title.trim(),
        requirements: form.requirements.trim(),
        cities: form.cities
          .split(/[,，、]/)
          .map((city) => city.trim())
          .filter(Boolean),
        exclude_keywords: form.exclude_keywords.trim(),
      };

      const response = await fetchJson<{ job_id: string; status: JobStatusType }>("/api/search-jobs", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      startTransition(() => {
        setJobId(response.job_id);
      });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "创建搜索任务失败");
    } finally {
      setSubmitting(false);
    }
  }

  function addToWorkspace(lane: WorkspaceLane, job: JobPosting) {
    setWorkspaceJobs((current) => {
      if (current[lane].some((item) => item.job_url === job.job_url)) {
        return current;
      }

      return {
        ...current,
        [lane]: [job, ...current[lane]],
      };
    });
  }

  function removeFromWorkspace(lane: WorkspaceLane, jobUrl: string) {
    setWorkspaceJobs((current) => ({
      ...current,
      [lane]: current[lane].filter((job) => job.job_url !== jobUrl),
    }));
  }

  function selectJob(job: JobPosting, openDetail = false) {
    setSelectedJobUrl(job.job_url);
    setDetailOpen(openDetail);
  }

  const completed = status?.status === "completed";
  const totalPinned = Object.values(workspaceJobs).reduce((count, laneJobs) => count + laneJobs.length, 0);
  const warnings = result?.result?.acceptance_summary?.warnings ?? result?.result?.search_warnings ?? [];
  const degradedMode = Boolean(result?.result?.degraded_mode ?? result?.result?.acceptance_summary?.degraded_mode);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-mark">
            <Radar />
          </div>
          <div>
            <p className="eyebrow">Campus / Internship Search Desk</p>
            <h1>通用校招与日常实习求职助手</h1>
          </div>
        </div>
        <div className="topbar-actions">
          <Badge variant={completed ? "success" : status?.status === "degraded" ? "warning" : status?.status === "failed" ? "danger" : "secondary"}>
            {status?.status ?? "idle"}
          </Badge>
        </div>
      </header>

      <Tabs defaultValue="live" className="page-shell">
        <div className="page-nav">
          <TabsList className="page-tabs-list">
            <TabsTrigger value="live">运行驾驶舱</TabsTrigger>
            <TabsTrigger value="results">岗位结果</TabsTrigger>
            <TabsTrigger value="workspace">投递工作台</TabsTrigger>
            <TabsTrigger value="output">输出报告</TabsTrigger>
          </TabsList>
          <div className="nav-stats">
            <span>{jobs.length} jobs</span>
            <span>{totalPinned} pinned</span>
            {degradedMode ? <span className="degraded-dot">degraded</span> : null}
          </div>
        </div>

        <TabsContent value="live">
          <main className="live-grid">
            <SearchPanel
              form={form}
              jobId={jobId}
              setForm={setForm}
              showAdvanced={showAdvanced}
              setShowAdvanced={setShowAdvanced}
              submitting={submitting}
              onSubmit={handleSubmit}
            />
            <LiveProgress status={status} />
            <EventConsole status={status} warnings={warnings} />
            <RunSummary status={status} result={result} degradedMode={degradedMode} />
          </main>
        </TabsContent>

        <TabsContent value="results">
          <main className="single-page-grid">
            <ResultsLedger
              jobs={jobs}
              result={result}
              selectedJobUrl={selectedJob?.job_url ?? null}
              onAddToWorkspace={addToWorkspace}
              onSelectJob={selectJob}
            />
          </main>
        </TabsContent>

        <TabsContent value="workspace">
          <main className="workspace-page-grid">
            <WorkspaceDock
              jobs={jobs}
              workspaceJobs={workspaceJobs}
              totalPinned={totalPinned}
              onAddToWorkspace={addToWorkspace}
              onRemoveFromWorkspace={removeFromWorkspace}
              onSelectJob={selectJob}
            />
          </main>
        </TabsContent>

        <TabsContent value="output">
          <main className="single-page-grid">
            <OutputReport result={result} status={status} warnings={warnings} />
          </main>
        </TabsContent>
      </Tabs>

      {error ? (
        <div className="toast-error" role="alert">
          {error}
        </div>
      ) : null}

      <JobDetailSheet job={selectedJob} open={detailOpen} onOpenChange={setDetailOpen} />
    </div>
  );
}

function SearchPanel({
  form,
  jobId,
  setForm,
  showAdvanced,
  setShowAdvanced,
  submitting,
  onSubmit,
}: {
  form: SearchFormState;
  jobId: string | null;
  setForm: React.Dispatch<React.SetStateAction<SearchFormState>>;
  showAdvanced: boolean;
  setShowAdvanced: React.Dispatch<React.SetStateAction<boolean>>;
  submitting: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Card className="panel-card search-card">
      <CardHeader>
        <div className="section-heading">
          <div>
            <CardTitle>搜索区</CardTitle>
            <CardDescription>只输入岗位名称即可启动，其他条件均可留空。</CardDescription>
          </div>
          <Search className="section-icon" />
        </div>
      </CardHeader>
      <CardContent>
        <form className="search-form" onSubmit={onSubmit}>
          <label className="field">
            <span>岗位名称</span>
            <Input
              value={form.job_title}
              onChange={(event) => setForm((current) => ({ ...current, job_title: event.target.value }))}
              placeholder="后端开发实习生 / 产品经理 / 数据分析"
            />
          </label>

          <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
            <CollapsibleTrigger asChild>
              <Button className="advanced-trigger" type="button" variant="ghost">
                <span>高级条件</span>
                <ChevronDown className={showAdvanced ? "chevron-open" : ""} />
              </Button>
            </CollapsibleTrigger>

            <CollapsibleContent className="advanced-fields">
              <label className="field">
                <span>岗位要求</span>
                <Textarea
                  rows={4}
                  value={form.requirements}
                  onChange={(event) => setForm((current) => ({ ...current, requirements: event.target.value }))}
                  placeholder="Java、SQL、Spring Boot、数据看板、英文沟通..."
                />
              </label>

              <div className="field-grid">
                <label className="field">
                  <span>求职类型</span>
                  <Select
                    value={form.search_type}
                    onValueChange={(value) =>
                      setForm((current) => ({
                        ...current,
                        search_type: value as SearchType,
                      }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">校招 / 实习都要</SelectItem>
                      <SelectItem value="campus">校招</SelectItem>
                      <SelectItem value="intern">日常实习</SelectItem>
                    </SelectContent>
                  </Select>
                </label>

                <label className="field">
                  <span>目标数量</span>
                  <Input
                    type="number"
                    min={1}
                    max={100}
                    value={form.target_count}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        target_count: Number(event.target.value || 30),
                      }))
                    }
                  />
                </label>
              </div>

              <label className="field">
                <span>城市</span>
                <Input
                  value={form.cities}
                  onChange={(event) => setForm((current) => ({ ...current, cities: event.target.value }))}
                  placeholder="上海, 北京, 杭州"
                />
              </label>

              <label className="field">
                <span>排除关键词</span>
                <Input
                  value={form.exclude_keywords}
                  onChange={(event) => setForm((current) => ({ ...current, exclude_keywords: event.target.value }))}
                  placeholder="销售、外包、资深"
                />
              </label>
            </CollapsibleContent>
          </Collapsible>

          <div className="form-actions">
            <Button type="submit" disabled={submitting}>
              {submitting ? <Loader2 className="spin-icon" /> : <Sparkles />}
              {submitting ? "正在创建任务" : "启动搜索"}
            </Button>
            {jobId ? <span className="task-chip">任务 {jobId.slice(0, 8)}</span> : null}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function LiveProgress({ status }: { status: JobStatusResponse | null }) {
  const stageEntries = Object.entries(STAGE_LABELS);
  const currentIndex = status ? stageEntries.findIndex(([stage]) => stage === status.stage) : -1;

  return (
    <Card className="panel-card progress-card">
      <CardHeader>
        <div className="section-heading">
          <div>
            <CardTitle>实时进度</CardTitle>
            <CardDescription>{status?.message ?? "提交岗位名称后开始接收 SSE 事件。"}</CardDescription>
          </div>
          <Clock3 className="section-icon" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="progress-head">
          <div>
            <p className="progress-label">当前阶段</p>
            <strong>{status ? STAGE_LABELS[status.stage] ?? status.stage : "等待任务"}</strong>
          </div>
          <span>{formatPercent(status?.progress ?? 0)}</span>
        </div>
        <Progress value={normalizePercent(status?.progress ?? 0)} />

        <div className="stage-list">
          {stageEntries.map(([key, label], index) => {
            const stageState =
              currentIndex === -1
                ? "idle"
                : index < currentIndex
                  ? "done"
                  : index === currentIndex
                    ? "active"
                    : "idle";

            return (
              <div className={`stage-row stage-${stageState}`} key={key}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong>{label}</strong>
                  <p>{key}</p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="metric-row">
          <Metric label="原始" value={status?.counts.raw_results ?? 0} />
          <Metric label="候选" value={status?.counts.candidate_jobs ?? 0} />
          <Metric label="最终" value={status?.counts.final_jobs ?? 0} />
        </div>

        <Separator />

        <div className="event-feed">
          <div className="feed-head">
            <strong>最近事件</strong>
            <span>{status?.updated_at ?? "waiting"}</span>
          </div>
          <ScrollArea className="feed-scroll">
            {(status?.recent_events?.length ? status.recent_events : [{ stage: "system", message: "任务执行时会在这里滚动刷新。", time: "" }]).map(
              (event, index) => (
                <div className="feed-row" key={`${event.time}-${index}`}>
                  <span>{STAGE_LABELS[event.stage] ?? event.stage}</span>
                  <p>{event.message}</p>
                </div>
              ),
            )}
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  );
}

function EventConsole({ status, warnings }: { status: JobStatusResponse | null; warnings: string[] }) {
  const events = status?.recent_events?.length
    ? status.recent_events
    : [{ stage: "system", message: "等待搜索任务启动。提交岗位名称后，这里会展示最新状态事件。", time: "" }];

  return (
    <Card className="panel-card event-console-card">
      <CardHeader>
        <div className="section-heading">
          <div>
            <CardTitle>最新事件流</CardTitle>
            <CardDescription>默认页面重点展示链路流转、实时日志和最后一次输出。</CardDescription>
          </div>
          <ClipboardList className="section-icon" />
        </div>
      </CardHeader>
      <CardContent>
        {warnings.length ? (
          <div className="warning-ribbon">
            {warnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        ) : null}
        <ScrollArea className="console-scroll">
          <div className="console-lines">
            {events.map((event, index) => (
              <div className="console-line" key={`${event.time}-${event.stage}-${index}`}>
                <span>{event.time ? event.time.split("T").pop() : "--:--:--"}</span>
                <strong>{STAGE_LABELS[event.stage] ?? event.stage}</strong>
                <p>{event.message}</p>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function RunSummary({
  status,
  result,
  degradedMode,
}: {
  status: JobStatusResponse | null;
  result: JobResultResponse | null;
  degradedMode: boolean;
}) {
  const acceptance = result?.result?.acceptance_summary;
  const optionalCoverage = (acceptance?.optional_field_coverage ?? {}) as Record<string, number>;

  return (
    <Card className="panel-card run-summary-card">
      <CardHeader>
        <div className="section-heading">
          <div>
            <CardTitle>状态快照</CardTitle>
            <CardDescription>一眼判断当前任务是否可继续使用。</CardDescription>
          </div>
          <Badge variant={degradedMode ? "warning" : result?.result?.acceptance_passed ? "success" : "outline"}>
            {degradedMode ? "搜索源不可用" : result?.result?.acceptance_passed ? "验收通过" : status?.stage ?? "idle"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="snapshot-grid">
          <Metric label="原始结果" value={status?.counts.raw_results ?? 0} />
          <Metric label="候选岗位" value={status?.counts.candidate_jobs ?? 0} />
          <Metric label="最终岗位" value={status?.counts.final_jobs ?? result?.result?.final_jobs.length ?? 0} />
          <Metric label="真实来源" value={(acceptance?.real_sources as string[] | undefined)?.length ?? 0} />
        </div>

        <div className="coverage-list">
          {["location", "salary", "requirements"].map((field) => (
            <div className="coverage-row" key={field}>
              <span>{field}</span>
              <Progress value={Math.round((optionalCoverage[field] ?? 0) * 100)} />
              <strong>{Math.round((optionalCoverage[field] ?? 0) * 100)}%</strong>
            </div>
          ))}
        </div>

        <Separator />

        <div className="latest-output">
          <span>最新输出</span>
          <p>{result?.result?.output_path || status?.output_path || "任务完成后会显示 JSON 输出路径。"}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function OutputReport({
  result,
  status,
  warnings,
}: {
  result: JobResultResponse | null;
  status: JobStatusResponse | null;
  warnings: string[];
}) {
  const payload = result?.result
    ? {
        status: result.status,
        acceptance_passed: result.result.acceptance_passed,
        acceptance_issues: result.result.acceptance_issues,
        acceptance_summary: result.result.acceptance_summary,
        sources_used: result.result.sources_used,
        output_path: result.result.output_path,
        summary_path: result.result.summary_path,
      }
    : status;

  return (
    <Card className="panel-card output-card">
      <CardHeader>
        <div className="section-heading">
          <div>
            <CardTitle>输出报告</CardTitle>
            <CardDescription>保留验收、warning、输出路径和最新状态 payload，方便定位失败原因。</CardDescription>
          </div>
          <Badge variant={result?.result?.acceptance_passed ? "success" : warnings.length ? "warning" : "outline"}>
            {result ? "result" : "status"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {warnings.length ? (
          <div className="warning-ribbon">
            {warnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        ) : null}

        {result?.result?.acceptance_issues?.length ? (
          <div className="issue-list output-issues">
            {result.result.acceptance_issues.map((issue) => (
              <div className="issue-row" key={issue}>
                <CheckCircle2 />
                <span>{issue}</span>
              </div>
            ))}
          </div>
        ) : null}

        <pre className="json-output">{JSON.stringify(payload ?? { message: "等待任务输出" }, null, 2)}</pre>
      </CardContent>
    </Card>
  );
}

function ResultsLedger({
  jobs,
  result,
  selectedJobUrl,
  onAddToWorkspace,
  onSelectJob,
}: {
  jobs: JobPosting[];
  result: JobResultResponse | null;
  selectedJobUrl: string | null;
  onAddToWorkspace: (lane: WorkspaceLane, job: JobPosting) => void;
  onSelectJob: (job: JobPosting, openDetail?: boolean) => void;
}) {
  return (
    <Card className="panel-card results-card">
      <CardHeader>
        <div className="section-heading">
          <div>
            <CardTitle>结果列表</CardTitle>
            <CardDescription>
              {result?.result?.output_path ? `输出：${result.result.output_path}` : "岗位会在任务完成后进入列表，可直接拖入右侧工作台。"}
            </CardDescription>
          </div>
          <Badge variant={result?.result?.acceptance_passed ? "success" : "outline"}>
            {jobs.length ? `${jobs.length} 个岗位` : "等待结果"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {result?.result ? (
          <>
            <div className="summary-bar">
              <Metric label="验收" value={result.result.acceptance_passed ? "通过" : "未通过"} />
              <Metric label="来源" value={(result.result.sources_used ?? []).length} />
              <Metric label="输出" value={jobs.length} />
            </div>

            <Tabs defaultValue="all" className="result-tabs">
              <TabsList>
                <TabsTrigger value="all">全部岗位</TabsTrigger>
                <TabsTrigger value="sources">来源统计</TabsTrigger>
                <TabsTrigger value="issues">验收备注</TabsTrigger>
              </TabsList>
              <TabsContent value="all">
                <ScrollArea className="job-scroll">
                  <div className="job-stack">
                    {jobs.map((job) => (
                      <JobCard
                        active={selectedJobUrl === job.job_url}
                        job={job}
                        key={job.job_url}
                        onAddToWorkspace={onAddToWorkspace}
                        onSelectJob={onSelectJob}
                      />
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>
              <TabsContent value="sources">
                <div className="source-grid">
                  {(result.result.sources_used ?? []).map((source) => (
                    <div className="source-row" key={source}>
                      <Layers3 />
                      <span>{source}</span>
                    </div>
                  ))}
                </div>
              </TabsContent>
              <TabsContent value="issues">
                <div className="issue-list">
                  {(result.result.acceptance_issues.length
                    ? result.result.acceptance_issues
                    : ["本轮验收暂无阻断问题。"]
                  ).map((issue) => (
                    <div className="issue-row" key={issue}>
                      <CheckCircle2 />
                      <span>{issue}</span>
                    </div>
                  ))}
                </div>
              </TabsContent>
            </Tabs>
          </>
        ) : (
          <div className="empty-panel">
            <BriefcaseBusiness />
            <h3>等待第一批岗位</h3>
            <p>左侧输入岗位名称并启动搜索后，SSE 会实时更新进度；任务完成后这里展示可拖拽岗位卡片。</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function JobCard({
  job,
  active,
  onAddToWorkspace,
  onSelectJob,
}: {
  job: JobPosting;
  active: boolean;
  onAddToWorkspace: (lane: WorkspaceLane, job: JobPosting) => void;
  onSelectJob: (job: JobPosting, openDetail?: boolean) => void;
}) {
  return (
    <article
      className={`job-card ${active ? "job-card-active" : ""}`}
      draggable
      onClick={() => onSelectJob(job)}
      onDragStart={(event) => {
        event.dataTransfer.effectAllowed = "copy";
        event.dataTransfer.setData("application/x-job-url", job.job_url);
      }}
    >
      <div className="job-card-grip" aria-hidden="true">
        <GripVertical />
      </div>
      <div className="job-card-main">
        <div className="job-card-title-row">
          <div>
            <h3>{job.title}</h3>
            <p>
              {job.company || "公司待补全"} · {job.location || "地点待补全"}
            </p>
          </div>
          <Badge variant="secondary">{job.source || "source"}</Badge>
        </div>

        <div className="job-card-meta">
          <span>
            <MapPin />
            {job.salary || "薪资待补全"}
          </span>
          <span>{job.experience_level || "类型待补全"}</span>
          {typeof job.confidence === "number" ? <span>{Math.round(job.confidence * 100)}% 匹配</span> : null}
        </div>

        <p className="job-card-desc">{job.requirements || job.description || "暂无结构化摘要，打开详情查看原始描述。"}</p>

        <div className="tag-line">
          {(job.tech_tags ?? []).slice(0, 6).map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>

        <div className="job-card-actions">
          <Button type="button" variant="outline" size="sm" onClick={(event) => withStop(event, () => onAddToWorkspace("favorites", job))}>
            <Star />
            收藏
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={(event) => withStop(event, () => onAddToWorkspace("compare", job))}>
            <GitCompareArrows />
            对比
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={(event) => withStop(event, () => onAddToWorkspace("applied", job))}>
            <Send />
            待投递
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={(event) => withStop(event, () => onSelectJob(job, true))}>
            详情
            <ArrowUpRight />
          </Button>
        </div>
      </div>
    </article>
  );
}

function WorkspaceDock({
  jobs,
  workspaceJobs,
  totalPinned,
  onAddToWorkspace,
  onRemoveFromWorkspace,
  onSelectJob,
}: {
  jobs: JobPosting[];
  workspaceJobs: Record<WorkspaceLane, JobPosting[]>;
  totalPinned: number;
  onAddToWorkspace: (lane: WorkspaceLane, job: JobPosting) => void;
  onRemoveFromWorkspace: (lane: WorkspaceLane, jobUrl: string) => void;
  onSelectJob: (job: JobPosting, openDetail?: boolean) => void;
}) {
  function handleDrop(lane: WorkspaceLane, event: React.DragEvent<HTMLElement>) {
    event.preventDefault();
    const jobUrl = event.dataTransfer.getData("application/x-job-url");
    const job = jobs.find((item) => item.job_url === jobUrl);
    if (job) {
      onAddToWorkspace(lane, job);
    }
  }

  return (
    <Card className="panel-card workspace-card">
      <CardHeader>
        <div className="section-heading">
          <div>
            <CardTitle>右侧工作台</CardTitle>
            <CardDescription>拖拽岗位卡，整理成收藏、对比、待投递。</CardDescription>
          </div>
          <Badge variant={totalPinned ? "default" : "outline"}>{totalPinned} pinned</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="lane-stack">
          {(Object.keys(WORKSPACE_LANES) as WorkspaceLane[]).map((lane) => {
            const config = WORKSPACE_LANES[lane];
            const Icon = config.icon;
            const laneJobs = workspaceJobs[lane];

            return (
              <section
                className="workspace-lane"
                key={lane}
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => handleDrop(lane, event)}
              >
                <div className="lane-head">
                  <div>
                    <strong>
                      <Icon />
                      {config.label}
                    </strong>
                    <p>{config.description}</p>
                  </div>
                  <span>{laneJobs.length}</span>
                </div>

                {laneJobs.length ? (
                  <div className="lane-items">
                    {laneJobs.map((job) => (
                      <div className="lane-item" key={job.job_url}>
                        <button type="button" onClick={() => onSelectJob(job, true)}>
                          <strong>{job.title}</strong>
                          <span>{job.company || "公司待补全"}</span>
                        </button>
                        <Button
                          aria-label={`移除 ${job.title}`}
                          size="icon"
                          type="button"
                          variant="ghost"
                          onClick={() => onRemoveFromWorkspace(lane, job.job_url)}
                        >
                          <Trash2 />
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="lane-empty">{config.empty}</div>
                )}
              </section>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function JobDetailSheet({
  job,
  open,
  onOpenChange,
}: {
  job: JobPosting | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        {job ? (
          <>
            <SheetHeader>
              <SheetTitle>{job.title}</SheetTitle>
              <SheetDescription>
                {job.company || "公司待补全"} · {job.location || "地点待补全"} · {job.salary || "薪资待补全"}
              </SheetDescription>
            </SheetHeader>

            <div className="detail-section">
              <h4>技能标签</h4>
              <div className="tag-line detail-tags">
                {(job.tech_tags ?? []).map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
            </div>

            <div className="detail-section">
              <h4>岗位要求</h4>
              <p>{job.requirements || "暂无结构化要求摘要。"}</p>
            </div>

            <div className="detail-section">
              <h4>岗位描述</h4>
              <p>{job.description || "暂无岗位描述。"}</p>
            </div>

            {job.job_url ? (
              <Button asChild className="detail-link-button">
                <a href={job.job_url} rel="noreferrer" target="_blank">
                  查看原始岗位
                  <ArrowUpRight />
                </a>
              </Button>
            ) : null}
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function withStop(event: React.MouseEvent, action: () => void) {
  event.stopPropagation();
  action();
}

export default App;
