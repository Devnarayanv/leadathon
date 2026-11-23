// Interface strings. Explanations themselves come from the backend; this only
// covers labels so the dashboard matches the chosen language.
const STRINGS = {
  en: {
    tagline: "Understand before you sign.",
    newAnalysis: "New analysis",
    privacy: "Privacy",
    analyseDocument: "Analyse a document",
    overview: "Document overview",
    filename: "File",
    docType: "Document type",
    pages: "Pages",
    status: "Status",
    analysed: "Analysed",
    keyInfo: "Important information",
    notFound: "Not found",
    attention: "Attention summary",
    clausesFlagged: "clauses flagged",
    clauseAnalysis: "Clauses needing attention",
    originalText: "Original text from your document",
    whyFlagged: "Why this was flagged",
    whatItSays: "What does the clause say?",
    plainMeaning: "What does it mean in simple terms?",
    whyAttention: "Why should I pay attention?",
    nextStep: "What could I do next?",
    uncertain: "What is uncertain?",
    suggestedAction: "Suggested next step",
    deadlines: "Deadlines",
    deadlineHint:
      "Tick a date only after checking it against the original document. Only ticked dates are exported.",
    exportCalendar: "Export ticked dates (.ics)",
    verified: "I checked this date",
    askTitle: "Ask this document",
    askPlaceholder: "e.g. What is the notice period?",
    ask: "Ask",
    evidence: "Evidence from your document",
    extractedText: "Extracted text",
    page: "Page",
    play: "Read aloud",
    stop: "Stop",
    language: "Language",
    confidence: "Confidence",
    source: "Source",
    bySource: { llm: "Local AI model", rules: "Rule engine" },
    expand: "Show details",
    collapse: "Hide details",
    noClauses:
      "No clauses matched the attention rules. That does not mean the document is safe, only that the rules found nothing to flag.",
    noFacts: "The rule engine could not read any key values from this document.",
    noDeadlines: "No dates in this document carried deadline wording.",
    summary: "Overview",
    warnings: "Notes about this analysis",
    retryAi: "Retry with AI",
    switching: "Updating explanations...",
    writtenFromRules: "Written from rule output, not from the AI model.",
    noSummary: "No summary was produced for this document.",
    textReadBy: "Text read by",
    pdfText: "PDF text layer",
    pdfTextOcr: "PDF text + OCR",
    uncertainTypeNote:
      "Document type uncertain. The facts are still read directly from the text, but the field names come from the closest matching type.",
    ocrNote:
      "Some pages had no selectable text, so OCR was used. OCR can misread characters — check any amount or date against the original.",
    nothingFlagged: "Nothing flagged",
    attentionSourceNote:
      "Attention indicators from the rule engine — not legal advice, and not a judgment that anything is illegal.",
    openFindings: "Open findings",
    readByRules: "Read from the text by rules",
    showSource: "source",
    hideSource: "hide",
    uncertainWord: "uncertain",
    offlineVoice: "offline voice",
    noVoice:
      "No voice is available for this language on this machine.",
    noVoiceShort: "No %s voice on this machine.",
    browserNoSpeech: "This browser does not support speech.",
    analysedIn: "analysed in",
    footerNote:
      "Doc Decode flags wording that deserves attention and explains it in simpler words. It does not decide whether anything is legal, valid or fair, and it can miss clauses. Check the original document and take professional advice before you sign, pay or reply.",
    askIntro:
      "Answers come only from your document's text. If it is not in there, the answer says so.",
    notInDocument: "not found in document",
    defaultVoice: "Default voice",
    voice: "Voice",
  },
  ml: {
    tagline: "ഒപ്പിടുന്നതിന് മുൻപ് മനസ്സിലാക്കുക.",
    newAnalysis: "പുതിയ പരിശോധന",
    privacy: "സ്വകാര്യത",
    analyseDocument: "രേഖ പരിശോധിക്കുക",
    overview: "രേഖയുടെ വിവരം",
    filename: "ഫയൽ",
    docType: "രേഖയുടെ തരം",
    pages: "പേജുകൾ",
    status: "നില",
    analysed: "പരിശോധിച്ചു",
    keyInfo: "പ്രധാന വിവരങ്ങൾ",
    notFound: "കണ്ടെത്തിയില്ല",
    attention: "ശ്രദ്ധിക്കേണ്ട കാര്യങ്ങൾ",
    clausesFlagged: "വാക്യങ്ങൾ അടയാളപ്പെടുത്തി",
    clauseAnalysis: "ശ്രദ്ധ വേണ്ട വാക്യങ്ങൾ",
    originalText: "രേഖയിലെ യഥാർത്ഥ വാക്യം",
    whyFlagged: "എന്തുകൊണ്ട് അടയാളപ്പെടുത്തി",
    whatItSays: "വാക്യം എന്താണ് പറയുന്നത്?",
    plainMeaning: "ലളിതമായി എന്താണ് അർത്ഥം?",
    whyAttention: "എന്തിന് ശ്രദ്ധിക്കണം?",
    nextStep: "അടുത്തത് എന്ത് ചെയ്യാം?",
    uncertain: "എന്താണ് വ്യക്തമല്ലാത്തത്?",
    suggestedAction: "നിർദ്ദേശിക്കുന്ന നടപടി",
    deadlines: "അവസാന തീയതികൾ",
    deadlineHint:
      "യഥാർത്ഥ രേഖയിൽ പരിശോധിച്ച ശേഷം മാത്രം തീയതി തിരഞ്ഞെടുക്കുക. തിരഞ്ഞെടുത്തവ മാത്രം കലണ്ടറിലേക്ക് നൽകും.",
    exportCalendar: "തിരഞ്ഞെടുത്ത തീയതികൾ (.ics)",
    verified: "ഈ തീയതി ഞാൻ പരിശോധിച്ചു",
    askTitle: "ഈ രേഖയോട് ചോദിക്കുക",
    askPlaceholder: "ഉദാ: നോട്ടീസ് കാലാവധി എത്ര?",
    ask: "ചോദിക്കുക",
    evidence: "രേഖയിൽ നിന്നുള്ള തെളിവ്",
    extractedText: "എടുത്ത വാചകം",
    page: "പേജ്",
    play: "വായിച്ചു കേൾക്കുക",
    stop: "നിർത്തുക",
    language: "ഭാഷ",
    confidence: "വിശ്വാസ്യത",
    source: "ഉറവിടം",
    bySource: { llm: "പ്രാദേശിക AI മോഡൽ", rules: "ചട്ട എൻജിൻ" },
    expand: "വിശദാംശങ്ങൾ",
    collapse: "മറയ്ക്കുക",
    noClauses:
      "ചട്ടങ്ങൾ പ്രകാരം ഒരു വാക്യവും അടയാളപ്പെടുത്തിയില്ല. രേഖ സുരക്ഷിതമാണ് എന്നല്ല അർത്ഥം.",
    noFacts: "ഈ രേഖയിൽ നിന്ന് പ്രധാന വിവരങ്ങൾ വായിക്കാനായില്ല.",
    noDeadlines: "അവസാന തീയതി സൂചിപ്പിക്കുന്ന വാക്യങ്ങൾ കണ്ടെത്തിയില്ല.",
    summary: "ചുരുക്കം",
    warnings: "ഈ പരിശോധനയെക്കുറിച്ചുള്ള കുറിപ്പുകൾ",
    retryAi: "AI ഉപയോഗിച്ച് വീണ്ടും",
    switching: "വിശദീകരണം പുതുക്കുന്നു...",
    writtenFromRules:
      "AI മോഡലിൽ നിന്നല്ല, ചട്ട എൻജിന്റെ ഫലത്തിൽ നിന്ന് എഴുതിയത്.",
    noSummary: "ഈ രേഖയ്ക്ക് ചുരുക്കം തയ്യാറാക്കിയിട്ടില്ല.",
    textReadBy: "വാചകം വായിച്ചത്",
    pdfText: "PDF വാചകം",
    pdfTextOcr: "PDF വാചകം + OCR",
    uncertainTypeNote:
      "രേഖയുടെ തരം ഉറപ്പില്ല. വിവരങ്ങൾ നേരിട്ട് വാചകത്തിൽ നിന്ന് തന്നെ വായിക്കുന്നു, എന്നാൽ ഫീൽഡ് പേരുകൾ ഏറ്റവും അടുത്ത തരത്തിൽ നിന്നാണ്.",
    ocrNote:
      "ചില പേജുകളിൽ തിരഞ്ഞെടുക്കാവുന്ന വാചകം ഇല്ലാത്തതിനാൽ OCR ഉപയോഗിച്ചു. OCR അക്ഷരങ്ങൾ തെറ്റായി വായിക്കാം — തുകയും തീയതിയും യഥാർത്ഥ രേഖയുമായി ഒത്തുനോക്കുക.",
    nothingFlagged: "ഒന്നും അടയാളപ്പെടുത്തിയില്ല",
    attentionSourceNote:
      "ചട്ട എൻജിന്റെ ശ്രദ്ധാ സൂചനകൾ — നിയമോപദേശമല്ല, എന്തെങ്കിലും നിയമവിരുദ്ധമാണെന്ന വിധിയുമല്ല.",
    openFindings: "കണ്ടെത്തലുകൾ തുറക്കുക",
    readByRules: "ചട്ടങ്ങൾ പ്രകാരം വാചകത്തിൽ നിന്ന് വായിച്ചത്",
    showSource: "ഉറവിടം",
    hideSource: "മറയ്ക്കുക",
    uncertainWord: "ഉറപ്പില്ല",
    offlineVoice: "ഓഫ്‌ലൈൻ ശബ്ദം",
    noVoice: "ഈ ഭാഷയ്ക്ക് ഈ ഉപകരണത്തിൽ ശബ്ദം ലഭ്യമല്ല.",
    noVoiceShort: "ഈ ഉപകരണത്തിൽ %s ശബ്ദം ഇല്ല.",
    browserNoSpeech: "ഈ ബ്രൗസർ സംസാരം പിന്തുണയ്ക്കുന്നില്ല.",
    analysedIn: "വിശകലനം ചെയ്തത്",
    footerNote:
      "ശ്രദ്ധ അർഹിക്കുന്ന വാചകങ്ങൾ Doc Decode അടയാളപ്പെടുത്തി ലളിതമായി വിശദീകരിക്കുന്നു. എന്തെങ്കിലും നിയമപരമാണോ ശരിയാണോ ന്യായമാണോ എന്ന് ഇത് തീരുമാനിക്കുന്നില്ല; ചില വാക്യങ്ങൾ വിട്ടുപോകാം. ഒപ്പിടുന്നതിനോ പണം നൽകുന്നതിനോ മറുപടി നൽകുന്നതിനോ മുൻപ് യഥാർത്ഥ രേഖ പരിശോധിക്കുകയും വിദഗ്ധാഭിപ്രായം തേടുകയും ചെയ്യുക.",
    askIntro:
      "ഉത്തരങ്ങൾ നിങ്ങളുടെ രേഖയിലെ വാചകത്തിൽ നിന്ന് മാത്രം. അതിൽ ഇല്ലെങ്കിൽ അങ്ങനെ തന്നെ പറയും.",
    notInDocument: "രേഖയിൽ കണ്ടെത്തിയില്ല",
    defaultVoice: "സ്വതവേയുള്ള ശബ്ദം",
    voice: "ശബ്ദം",
  },
};

export function t(language, key) {
  const pack = STRINGS[language] ?? STRINGS.en;
  return pack[key] ?? STRINGS.en[key] ?? key;
}

// Document type names for the type the backend reports. The backend also
// localises its own copy, but a language switch reuses the existing result, so
// the label has to be resolvable here too.
export const DOC_TYPES = {
  invoice: { en: "Invoice", ml: "ഇൻവോയ്സ്" },
  purchase_order: { en: "Purchase order", ml: "പർച്ചേസ് ഓർഡർ" },
  tender: { en: "Tender notice", ml: "ടെൻഡർ അറിയിപ്പ്" },
  gst_notice: { en: "GST notice", ml: "GST അറിയിപ്പ്" },
  rental_agreement: { en: "Rental agreement", ml: "വാടക കരാർ" },
  loan_agreement: { en: "Loan document", ml: "വായ്പ രേഖ" },
  contract: { en: "Contract / service agreement", ml: "കരാർ / സേവന കരാർ" },
  insurance: { en: "Insurance policy", ml: "ഇൻഷുറൻസ് പോളിസി" },
  hospital_bill: { en: "Hospital bill", ml: "ആശുപത്രി ബിൽ" },
  financial_statement: { en: "Financial statement", ml: "സാമ്പത്തിക പ്രസ്താവന" },
  business_license: { en: "Business licence / registration", ml: "വ്യാപാര ലൈസൻസ് / രജിസ്ട്രേഷൻ" },
  legal_notice: { en: "Legal notice", ml: "നിയമ അറിയിപ്പ്" },
  government_notice: { en: "Government notice", ml: "സർക്കാർ അറിയിപ്പ്" },
  other: { en: "Other / uncategorised", ml: "മറ്റുള്ളവ / വർഗ്ഗീകരിക്കാത്തത്" },
};

// `fallback` is the backend's own label, used only for a type we do not know.
export function docTypeLabel(docType, fallback, language) {
  const entry = DOC_TYPES[docType];
  if (!entry) return fallback || docType || "";
  return entry[language] ?? entry.en;
}

export const ATTENTION_LABELS = {
  en: {
    attention: "Attention required",
    financial: "Financial condition",
    deadline: "Important deadline",
    unusual: "Unusual condition",
    info: "For information",
  },
  ml: {
    attention: "ശ്രദ്ധ ആവശ്യം",
    financial: "പണപരമായ വ്യവസ്ഥ",
    deadline: "പ്രധാന തീയതി",
    unusual: "അസാധാരണ വ്യവസ്ഥ",
    info: "വിവരത്തിന്",
  },
};

export const CONFIDENCE_LABELS = {
  en: { high: "High confidence", medium: "Medium confidence", low: "Low confidence" },
  ml: { high: "ഉയർന്ന വിശ്വാസ്യത", medium: "മധ്യമ വിശ്വാസ്യത", low: "കുറഞ്ഞ വിശ്വാസ്യത" },
};
