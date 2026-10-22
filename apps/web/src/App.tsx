import { lazy, Suspense } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import { NewProductPage } from "./routes/NewProductPage";
import { NewTaskPage } from "./routes/NewTaskPage";
import { CompareVersionsPage } from "./routes/CompareVersionsPage";
import { ApprovalReplayPage } from "./routes/ApprovalReplayPage";
import { GenerateScriptPage } from "./routes/GenerateScriptPage";
import { EvidenceArtifactsPage } from "./routes/EvidenceArtifactsPage";
import { JobPage } from "./routes/JobPage";
import { MissionControlPage } from "./routes/MissionControlPage";
import { ProductDetailPage } from "./routes/ProductDetailPage";
import { ProductsPage } from "./routes/ProductsPage";
import { ScriptPage } from "./routes/ScriptPage";
import { StoryboardPreflightPage } from "./routes/StoryboardPreflightPage";
import { StoryboardReviewPage } from "./routes/StoryboardReviewPage";
import { TaskInboxPage } from "./routes/TaskInboxPage";

const DecisionWorkbenchPrototypePage = import.meta.env.DEV
  ? lazy(() => import("./routes/DecisionWorkbenchPrototypePage").then((module) => ({ default: module.DecisionWorkbenchPrototypePage })))
  : null;

export function AppRoutes() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/products" className="brand" aria-label="FactFrame 首页">
          <span className="brand-mark">FF</span>
          <span>FactFrame</span>
        </NavLink>
        <nav aria-label="主导航">
          <NavLink to="/sv-agent/tasks">SV-Agent</NavLink>
          <NavLink to="/products">商品事实</NavLink>
          <span className="nav-muted">脚本版本</span>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/products" replace />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/sv-agent/tasks" element={<TaskInboxPage />} />
          <Route path="/sv-agent/tasks/new" element={<NewTaskPage />} />
          <Route path="/sv-agent/tasks/:taskId/approval-replay" element={<ApprovalReplayPage />} />
          <Route path="/sv-agent/tasks/:taskId/evidence" element={<EvidenceArtifactsPage />} />
          <Route path="/sv-agent/tasks/:taskId" element={<MissionControlPage />} />
          <Route path="/products/new" element={<NewProductPage />} />
          <Route path="/products/:id" element={<ProductDetailPage />} />
          <Route path="/products/:id/generate" element={<GenerateScriptPage />} />
          <Route path="/jobs/:id" element={<JobPage />} />
          <Route path="/scripts/:id/versions/:versionId/storyboard-preflight" element={<StoryboardPreflightPage />} />
          <Route path="/storyboards/:id" element={<StoryboardReviewPage />} />
          <Route path="/scripts/:id" element={<ScriptPage />} />
          <Route path="/scripts/:id/compare" element={<CompareVersionsPage />} />
          {DecisionWorkbenchPrototypePage && <Route path="/prototype/momcozy-decision-workbench" element={<Suspense fallback={<div className="state-card">正在打开原型…</div>}><DecisionWorkbenchPrototypePage /></Suspense>} />}
        </Routes>
      </main>
    </div>
  );
}
