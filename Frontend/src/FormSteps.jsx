// src/FormSteps.jsx
import React, { useState, useRef, useCallback, Fragment, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import BasicInfo from './components/BasicInfo.jsx';
import UploadFiles from './components/UploadFiles.jsx';
import Settings from './components/Settings.jsx';
import Design from './components/Design.jsx';
import Capabilities from './components/Capabilities.jsx';
import Test from './components/Test.jsx';
import Deploy from './components/Deploy.jsx';

import GreekFlag from './assets/greekflag.jpg';
import UkFlag from './assets/ukflag.jpg';


export default function FormSteps({
  currentPage,
  steps,
  onNext,
  onPrev,
  onFormSubmit,
  apiKey,
  widgetScript,
  inheritedFormData,
  initialData = {},
}) {
  const { t, i18n } = useTranslation();

  const [formData, setFormData] = useState({
    botName: '',
    greeting: '',
    persona: '',
    botRestrictions: '',
    companyName: '',
    websiteURL: '',
    industry: '',
    industryOther: '',
    description: '',
    keywords: '',
    allowedDomains: '',
    primaryColor: '#4f46e5',
    position: 'Bottom Right',
    themeStyle: 'Minimal',
    suggestedPrompts: '',
      // 👇 ΠΡΟΣΘΗΚΗ
    appointmentSettings: {
      slotDuration: 30,         // 15/30/45/60
      workStart: '09:00',       // ώρα έναρξης
      workEnd: '17:00',         // ώρα λήξης
      workDays: ['Mon','Tue','Wed','Thu','Fri'],
    ...initialData}
  });

  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const uploadFilesRef = useRef(null);

  const [logoFile, setLogoFile] = useState(null); //new
  const [botAvatarFile, setBotAvatarFile] = useState(null); //new
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [faqItems, setFaqItems] = useState([{ question: '', answer: '' }]);

  // Default values για κάθε bot type
  const botTypeDefaults = {
    Sales: {
      botName: "Sales Assistant",
      greeting: "Hello! How can I help you today?",
      persona: "Professional and trustworthy, helpful and consultative, enthusiastic about company's offerings, respectful of customer's decision-making process"
    },
    Support: {
      botName: "Support Helper", 
      greeting: "Hi there! What can I assist you with?",
      persona: "Empathetic and understanding, patient and helpful, clear and instructional, professional and reassuring, honest about limitations"
    },
    FAQ: {
      botName: "Info Bot",
      greeting: "Welcome! What would you like to know?", 
      persona: "Informative and precise, well-organized and clear, professional and reliable, direct but helpful"
   },
    Onboarding: {
      botName: "Welcome Guide",
      greeting: "Hello! I'm here to help you get started.",
      persona: "Welcoming and encouraging, patient and supportive, educational without being overwhelming, positive and motivational"  
   }
 };

// Auto-fill effect
  useEffect(() => {
    if (formData.botTypePreset && botTypeDefaults[formData.botTypePreset]) {
      const defaults = botTypeDefaults[formData.botTypePreset];
    
      setFormData(prev => ({
        ...prev,
        botName: defaults.botName,
        greeting: defaults.greeting, 
        personaSelect: defaults.persona
      }));
    } else if (formData.botTypePreset === '') {
      setFormData(prev => ({
        ...prev,
        botName: '',
        greeting: '',
        persona: ''
     }));
    }
  }, [formData.botTypePreset]);


  const handleInputChange = useCallback(
    (e) => {
      const { name, value, files } = e.target;
    
    // Handle file inputs
      if (files && files.length > 0) {
        if (name === 'logo') {
          setLogoFile(files[0]);
    // Αν δεν υπάρχει botAvatar, χρησιμοποίησε το λογότυπο
          if (!botAvatarFile) {
            setBotAvatarFile(files[0]);
          }
      } else if (name === 'botAvatar') {
        setBotAvatarFile(files[0]);
      }
      return;
    }
    
    // Handle regular inputs
      setFormData((prev) => ({ ...prev, [name]: value }));
      if (errors[name]) setErrors((prev) => ({ ...prev, [name]: null }));
    },
    [errors]
 );

  const handleSubmit = async (e) => {
  if (e) e.preventDefault();
  setIsSubmitting(true);
  try {
    const files = selectedFiles;
    const faqData = faqItems
    
    // Get FAQ data from UploadFiles component
    
    console.log("FAQ data from UploadFiles:", faqData);
    
    // Add FAQ to form data
    const formDataWithFaq = {...formData, faqItems: faqData};
    console.log("Form data with FAQ:", formDataWithFaq);
    
    const formDataToSend = new FormData();
    formDataToSend.append('company_info', JSON.stringify(formDataWithFaq));
    files.forEach((file) => formDataToSend.append('files', file));
    
    // Add logo and botAvatar files
    if (logoFile) {
      formDataToSend.append('logo', logoFile);
    }
    if (botAvatarFile) {
      formDataToSend.append('botAvatar', botAvatarFile);
    }
    console.log("Files from upload:", files);
    console.log("Logo file:", logoFile);  
    console.log("Bot avatar file:", botAvatarFile);
    console.log("FormData entries:");
    for (let [key, value] of formDataToSend.entries()) {
      console.log(key, value);
    }
    
    await onFormSubmit(formDataToSend);
  } finally {
    setTimeout(() => setIsSubmitting(false), 400);
  }
};

  const commonProps = { 
    formData, 
    handleInputChange, 
    errors, 
    logoPreview: logoFile, 
    botAvatar: botAvatarFile,
    selectedFiles,
    onFilesChange: setSelectedFiles,
    faqItems,
    onFaqChange: setFaqItems 
 };
  const changeLang = (lng) => i18n.changeLanguage(lng);

  // ---- Compact mobile stepper (numbers only) ----
  const MobileStep = ({ index }) => {
    const isDone = index < currentPage;
    const isActive = index === currentPage;

    const base =
      'relative flex items-center justify-center rounded-full border shrink-0 ' +
      'w-6 h-6 text-[11px] max-[360px]:w-5 max-[360px]:h-5 max-[360px]:text-[10px] ' +
      'max-[320px]:w-4 max-[320px]:h-4 max-[320px]:text-[9px] ' +
      'transition-transform';

    let cls = '';
    if (isDone) {
      cls = `${base} bg-indigo-600 border-indigo-600 text-white`;
    } else if (isActive) {
      // ΠΙΟ ΕΝΤΟΝΟ active: παχύτερο περίγραμμα + ring
      cls = `${base} bg-white border-2 border-indigo-600 text-indigo-700 ring-2 ring-indigo-300`;
    } else {
      cls = `${base} bg-white border-slate-300 text-slate-500`;
    }

    return (
      <div className="flex items-center">
        <div
          className={cls}
          aria-current={isActive ? 'step' : undefined}
          aria-label={t('formSteps.stepOfTotal', {
            defaultValue: 'Step {{current}} of {{total}}',
            current: index + 1,
            total: steps.length,
          })}
        >
          {isDone ? (
            <svg
              viewBox="0 0 24 24"
              className="w-3 h-3 max-[360px]:w-2.5 max-[360px]:h-2.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M20 6L9 17l-5-5" />
            </svg>
          ) : (
            <span className="font-semibold">{index + 1}</span>
          )}
        </div>
      </div>
    );
  };

  const MobileStepper = () => (
    <div className="lg:hidden mt-2">
      <div className="px-2 py-2 bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between w-full">
          {steps.map((_, idx) => (
            <Fragment key={idx}>
              <MobileStep index={idx} />
              {idx < steps.length - 1 && (
                <div
                  className={[
                    'flex-1 h-0.5 mx-1',
                    idx < currentPage ? 'bg-indigo-600' : 'bg-slate-300',
                  ].join(' ')}
                  aria-hidden="true"
                />
              )}
            </Fragment>
          ))}
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Header (flags + title + mobile stepper) */}
      <div className="mb-8">
        {/* γλώσσες */}
        <div className="flex justify-end gap-3 mb-4">
          <img
            src={UkFlag}
            alt={t('formSteps.altEnglish', 'English')}
            className={`w-7 h-5 cursor-pointer rounded shadow ${i18n.language === 'en' ? 'ring-2 ring-indigo-500' : ''}`}
            onClick={() => changeLang('en')}
          />
        <img
            src={GreekFlag}
            alt={t('formSteps.altGreek', 'Ελληνικά')}
            className={`w-7 h-5 cursor-pointer rounded shadow ${i18n.language === 'el' ? 'ring-2 ring-indigo-500' : ''}`}
            onClick={() => changeLang('el')}
          />
        </div>

        {/* Τίτλος τρέχοντος βήματος – με αριθμό μπροστά (π.χ. "5. Εμφάνιση & Branding") */}
        <p className="text-sm font-medium text-indigo-600" aria-live="polite" aria-atomic="true">
          {(currentPage + 1) + '. '}{steps[currentPage]}
        </p>

        {/* Compact numeric stepper μόνο στο mobile */}
        <MobileStepper />
      </div>

      <form onSubmit={handleSubmit}>
        <div className="min-h-[450px]">
          {currentPage === 0 && <BasicInfo {...commonProps} />}
          {currentPage === 1 && <UploadFiles {...commonProps} ref={uploadFilesRef} />}
          {currentPage === 2 && <Settings {...commonProps} />}
          {currentPage === 3 && <Capabilities {...commonProps} />}
          {currentPage === 4 && <Design {...commonProps} />}
          {currentPage === 5 && (
            <Test
              formData={inheritedFormData || formData}
              apiKey={apiKey}
              serverUrl="http://127.0.0.1:8000/chat"
            />
          )}
          {currentPage === 6 && <Deploy {...commonProps} apiKey={apiKey} widgetScript={widgetScript} />}
        </div>

        <div className={`flex pt-6 ${currentPage > 0 ? 'justify-between' : 'justify-end'}`}>
          {currentPage > 0 && (
            <button
              type="button"
              onClick={onPrev}
              className="text-slate-600 font-medium py-3 px-6 rounded-lg bg-slate-100"
            >
              {t('back')}
            </button>
          )}

          {currentPage < steps.length - 1 && (
            <button
              type="button"
              onClick={currentPage === 4 ? handleSubmit : onNext}
              className="bg-indigo-600 text-white font-bold py-3 px-6 rounded-lg"
              disabled={currentPage === 4 && isSubmitting}
            >
              {currentPage === 4 ? (isSubmitting ? t('submitting') : t('createChatbot', 'Create Chatbot')) : t('next')}
            </button>
          )}

          {currentPage === steps.length - 1 && (
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-indigo-600 text-white font-bold py-3 px-6 rounded-lg disabled:bg-slate-400 disabled:cursor-not-allowed"
            >
              {isSubmitting ? t('submitting') : t('submit')}
            </button>
          )}
        </div>
      </form>
    </>
  );
}