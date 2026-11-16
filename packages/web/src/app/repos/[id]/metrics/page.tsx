import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { BarChart3 } from "lucide-react";
import { PageShell } from "@repowise-dev/ui/shared";
import { MetricsView } from "@/components/metrics/metrics-view";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("views.metrics");
  return { title: t("title") };
}

export default async function MetricsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const t = await getTranslations("views.metrics");
  return (
    <PageShell title={t("title")} icon={<BarChart3 />} description={t("description")} maxWidth="wide">
      <MetricsView key={id} repoId={id} />
    </PageShell>
  );
}
