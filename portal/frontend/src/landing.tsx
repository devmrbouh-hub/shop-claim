import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import LandingLayout from "@/layouts/LandingLayout";
import LandingPage from "@/pages/landing/LandingPage";
import OfferPage from "@/pages/landing/OfferPage";
import PrivacyPage from "@/pages/landing/PrivacyPage";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <TooltipProvider>
        <Routes>
          <Route element={<LandingLayout standalone={import.meta.env.PROD} user={null} />}>
            <Route index element={<LandingPage standalone={import.meta.env.PROD} />} />
            <Route path="offer" element={<OfferPage />} />
            <Route path="privacy" element={<PrivacyPage />} />
          </Route>
        </Routes>
        <Toaster richColors position="top-center" />
      </TooltipProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
