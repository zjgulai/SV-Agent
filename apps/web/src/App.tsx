import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import { NewProductPage } from "./routes/NewProductPage";
import { CompareVersionsPage } from "./routes/CompareVersionsPage";
import { GenerateScriptPage } from "./routes/GenerateScriptPage";
import { JobPage } from "./routes/JobPage";
import { ProductDetailPage } from "./routes/ProductDetailPage";
import { ProductsPage } from "./routes/ProductsPage";
import { ScriptPage } from "./routes/ScriptPage";
import { StoryboardPreflightPage } from "./routes/StoryboardPreflightPage";
import { StoryboardReviewPage } from "./routes/StoryboardReviewPage";

export function AppRoutes() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/products" className="brand" aria-label="FactFrame 首页">
          <span className="brand-mark">FF</span>
          <span>FactFrame</span>
        </NavLink>
        <nav aria-label="主导航">
          <NavLink to="/products">商品事实</NavLink>
          <span className="nav-muted">脚本版本</span>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/products" replace />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/products/new" element={<NewProductPage />} />
          <Route path="/products/:id" element={<ProductDetailPage />} />
          <Route path="/products/:id/generate" element={<GenerateScriptPage />} />
          <Route path="/jobs/:id" element={<JobPage />} />
          <Route path="/scripts/:id/versions/:versionId/storyboard-preflight" element={<StoryboardPreflightPage />} />
          <Route path="/storyboards/:id" element={<StoryboardReviewPage />} />
          <Route path="/scripts/:id" element={<ScriptPage />} />
          <Route path="/scripts/:id/compare" element={<CompareVersionsPage />} />
        </Routes>
      </main>
    </div>
  );
}
