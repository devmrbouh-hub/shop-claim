import CaseStudy from "./CaseStudy";
import FaqAccordion from "./FaqAccordion";
import FitChecklist from "./FitChecklist";
import HeroSection from "./HeroSection";
import IncludesList from "./IncludesList";
import LeadForm from "./LeadForm";
import PricingCards from "./PricingCards";
import StepsGrid from "./StepsGrid";
import WhyShopClaim from "./WhyShopClaim";

type Props = { standalone?: boolean };

export default function LandingPage({ standalone }: Props) {
  return (
    <main className="flex-1">
      <HeroSection standalone={standalone} />
      <StepsGrid />
      <WhyShopClaim />
      <FitChecklist />
      <IncludesList />
      <CaseStudy />
      <PricingCards standalone={standalone} />
      <FaqAccordion />
      <LeadForm standalone={standalone} />
    </main>
  );
}
