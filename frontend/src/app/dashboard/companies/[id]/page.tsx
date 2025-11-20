// For static export with dynamic routes, we need to generate at least one param
// The actual routing is handled client-side via useParams and router
export function generateStaticParams() {
  // Return a placeholder - Next.js will generate this route
  // Client-side routing will handle the actual company ID from the URL
  return [{ id: "placeholder" }];
}

// Server component wrapper - just renders the client component
import React from "react";
import CompanyDetailPage from "./page-client";

export default function Page() {
  return <CompanyDetailPage />;
}
