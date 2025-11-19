// Required for static export with dynamic routes
// Return a placeholder to satisfy static export requirements
// Actual routing is handled client-side
export function generateStaticParams() {
  return [{ id: "placeholder" }];
}

// Server component wrapper for static export
import React from "react";
import CompanyDetailPage from "./page-client";

export default function Page() {
  return <CompanyDetailPage />;
}
