import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import MobileNav from "./components/MobileNav";
import Dashboard from "./pages/Dashboard";
import Products from "./pages/Products";
import BoxAnalysis from "./pages/BoxAnalysis";
import Comparison from "./pages/Comparison";
import Portfolio from "./pages/Portfolio";

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      {/* pb-16 on mobile reserves space above the fixed bottom nav */}
      <main className="flex-1 overflow-y-auto p-4 pb-20 md:p-6 md:pb-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/products" element={<Products />} />
          <Route path="/ev" element={<BoxAnalysis />} />
          <Route path="/compare" element={<Comparison />} />
          <Route path="/portfolio" element={<Portfolio />} />
        </Routes>
      </main>
      <MobileNav />
    </div>
  );
}
