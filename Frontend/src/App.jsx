// App.jsx
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import FormSteps from './FormSteps';
import SidebarPreview from './components/SidebarPreview';
import LoadingPage from './components/LoadingPage';

export default function App() {
  const { t } = useTranslation();

  // --- State ---
  const [formData, setFormData] = useState({});
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [leftWebsite, setLeftWebsite] = useState('');
  const [apiKey, setApiKey] = useState(null);
  const [widgetScript, setWidgetScript] = useState(null);

  // Loading/Progress
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(null);

  // --- Πλοήγηση βημάτων ---
  const [currentPage, setCurrentPage] = useState(0);
  const [maxVisitedPage, setMaxVisitedPage] = useState(0);

  // --- Mobile steps dropdown state ---
  const [showMobileSteps, setShowMobileSteps] = useState(false);

  // Παίρνει τις μεταφράσεις των βημάτων
  const stepLabels = t('steps', { returnObjects: true }) || {};
  const steps = Object.values(stepLabels);

  const handleNext = () => {
    if (currentPage < steps.length - 1) {
      const newPage = currentPage + 1;
      setCurrentPage(newPage);
      if (newPage > maxVisitedPage) setMaxVisitedPage(newPage);
    }
  };

  const handlePrev = () => {
    if (currentPage > 0) setCurrentPage(currentPage - 1);
  };

  const handleGoToPage = (pageIndex) => {
    if (pageIndex <= maxVisitedPage) {
      setCurrentPage(pageIndex);
      setShowMobileSteps(false); // κλείσιμο dropdown μετά την επιλογή
    }
  };

  const ACCENT_TITLE = 'indigo';
  const titleClass = {
    indigo: 'text-indigo-400',
    teal: 'text-teal-400',
    amber: 'text-amber-400',
    cyan: 'text-cyan-400',
  }[ACCENT_TITLE];

  // Υποβολή φόρμας
  const handleFormSubmit = async (finalData) => {
    let interval = null;
    try {
      setLoading(true);
      setProgress(8);
      interval = setInterval(() => {
        setProgress((p) => (p === null ? 8 : Math.min(p + Math.random() * 8, 92)));
      }, 700);

      const res = await fetch('http://127.0.0.1:8000/create_chatbot', {
        method: 'POST',
        body: finalData,
      });
      if (!res.ok) throw new Error('create_chatbot failed');

      const responseData = await res.json();
      setApiKey(responseData.api_key);
      setWidgetScript(responseData.widget_script);

      clearInterval(interval);
      setProgress(100);
      setTimeout(() => {
        const companyInfoStr = finalData.get('company_info');
        const companyData = JSON.parse(companyInfoStr);
        setFormData((prev) => ({ ...prev, ...companyData }));
        setLeftWebsite(companyData.websiteURL || '');
        setLoading(false);
        setProgress(null);
        setCurrentPage((prev) => prev + 1);
      }, 300);
    } catch (error) {
      if (interval) clearInterval(interval);
      setLoading(false);
      setProgress(null);
      console.error(error);
      alert('Κάτι πήγε στραβά. Δοκίμασε ξανά.');
    }
  };

  const mobileStepLabel = t('formSteps.stepShortOfTotal', {
    defaultValue: 'Βήμα {{current}} από {{total}}',
    current: currentPage + 1,
    total: steps.length,
  });

  return (
    <div className="min-h-screen font-sans">
      {/* Mobile Header — τίτλος + dropdown με "Βήμα X από Y" */}
      <div className="lg:hidden bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="px-4 py-3 flex items-center justify-between">
          <h1 className={`text-xl font-bold ${titleClass}`}>{t('appTitle')}</h1>

          {!formSubmitted && !loading && (
            <button
              onClick={() => setShowMobileSteps((s) => !s)}
              className="flex items-center space-x-2 text-gray-700 hover:text-gray-900 transition-colors"
              aria-expanded={showMobileSteps}
              aria-controls="mobile-steps"
            >
              <span className="text-sm font-medium">{mobileStepLabel}</span>
              <svg
                className={`w-4 h-4 transform transition-transform ${showMobileSteps ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}
        </div>

        {/* Dropdown με τα βήματα (μόνο mobile) */}
        {showMobileSteps && !formSubmitted && !loading && (
          <div id="mobile-steps" className="border-t border-gray-200 bg-white shadow-lg">
            <div className="px-4 py-2">
              <SidebarPreview
                steps={steps}
                currentPage={currentPage}
                maxVisitedPage={maxVisitedPage}
                onGoToPage={handleGoToPage}
                isMobile={true}
              />
            </div>
          </div>
        )}
      </div>

      <div className="flex min-h-screen lg:min-h-screen">
        {/* Desktop Sidebar (fixed πλάτος) */}
        <div className="hidden lg:flex bg-gray-100 pl-6 pr-4 py-8 flex-col border-r border-gray-200 lg:w-72 flex-none">
          {!formSubmitted ? (
            <SidebarPreview
              steps={steps}
              currentPage={currentPage}
              maxVisitedPage={maxVisitedPage}
              onGoToPage={handleGoToPage}
            />
          ) : (
            <div className="z-10 flex flex-col justify-between h-full">
              <div>
                <h1 className={`text-3xl font-bold ${titleClass}`}>{t('appTitle')}</h1>
                <p className="mt-4 text-gray-600 font-light tracking-wide">
                  {t('chatActiveSubtitle')}
                </p>
              </div>
              <div className="mt-10 flex items-center justify-center min-h-[280px]" />
              <div>
                <p className="text-sm text-gray-500">© 2025 Your Company</p>
              </div>
            </div>
          )}
        </div>

        {/* Κύρια περιοχή — left aligned, χωρίς μεγάλο κενό */}
        <div className="w-full lg:flex-1 bg-zinc-50 min-h-screen lg:min-h-auto">
          <div className={`w-full ${loading ? 'flex items-center justify-center min-h-screen lg:min-h-auto' : ''}`}>
            <div className="px-4 sm:px-6 lg:px-10 py-4 sm:py-6 lg:py-10">
              <div className="max-w-3xl xl:max-w-4xl">
                {formSubmitted ? (
                  <div className="w-full">
                    <ChatBubble chatbotData={formData} apiKey={apiKey} />
                  </div>
                ) : loading ? (
                  <div className="w-full max-w-2xl">
                    <LoadingPage
                      title={t('creatingChatbotTitle')}
                      subtitle={t('creatingChatbotSubtitle')}
                      progress={progress}
                      tips={[t('dontClosePage'), t('willNotifyWhenReady')]}
                    />
                  </div>
                ) : (
                  <div className="w-full pt-4 lg:pt-0">
                    <FormSteps
                      currentPage={currentPage}
                      steps={steps}
                      onNext={handleNext}
                      onPrev={handlePrev}
                      onFormSubmit={handleFormSubmit}
                      apiKey={apiKey}
                      widgetScript={widgetScript}
                      inheritedFormData={formData}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Overlay όταν είναι ανοικτό το dropdown στο mobile */}
      {showMobileSteps && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setShowMobileSteps(false)}
        />
      )}
    </div>
  );
}
