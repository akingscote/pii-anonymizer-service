import { useState, useMemo } from "react";
import { anonymizeText, type AnonymizeResponse, type Substitution } from "../services/api";

// Sample texts for experimentation
const SAMPLE_TEXTS = [
  {
    name: "Customer Support Email",
    text: `Dear Support Team,

My name is John Smith and I'm having trouble with my account. You can reach me at john.smith@example.com or call me at (555) 123-4567.

My credit card number is 4242424242424242 and my billing address is 123 Main Street, San Francisco, CA 94102.

Please help me resolve this issue as soon as possible.

Best regards,
John Smith`,
  },
  {
    name: "Medical Record Note",
    text: `Patient: Sarah Johnson
Date of Birth: 03/15/1985
SSN: 456-78-9012
Phone: (555) 987-6543
Email: sarah.j@healthmail.com

Chief Complaint: Patient presents with recurring headaches.
Referred by: Dr. Michael Chen at City Medical Center, Los Angeles.

Member ID: 12345678
Emergency Contact: Robert Johnson at (555) 111-2222`,
  },
  {
    name: "HR Onboarding Form",
    text: `New Employee Information:

Name: Emily Davis
Email: emily.davis@company.com
Personal Email: emilyd92@gmail.com
Phone: 555-234-5678
Address: 456 Oak Avenue, Apt 12B, Seattle, WA 98101

Bank Details for Direct Deposit:
Account Holder: Emily Davis
Routing: 021000089
Account: 1234567890

Emergency Contact: Michael Davis (Spouse)
Phone: (555) 345-6789`,
  },
  {
    name: "Legal Document",
    text: `CONFIDENTIAL SETTLEMENT AGREEMENT

Between: ABC Corporation
And: Jane Williams (SSN: 234-56-7890)

Ms. Williams, residing at 789 Pine Road, Chicago, IL 60601, agrees to the terms outlined below.

Contact Information:
- Attorney: Robert Martinez, Esq.
- Email: r.martinez@lawfirm.com
- Phone: (312) 555-0100

Payment to be sent to:
Credit Card: 4111111111111111
Exp: 12/25

Signed on January 15, 2024 in Chicago, Illinois.`,
  },
  {
    name: "IT Support Ticket",
    text: `Ticket #45231
Submitted by: Alex Thompson
Email: alex.t@techcorp.io
IP Address: 192.168.1.105
MAC Address: 00:1B:44:11:3A:B7

Issue: Cannot access server at 10.0.0.50

User's workstation: WS-THOMPSON-01
Location: Building A, Floor 3, New York office

Please contact me at ext. 4521 or mobile (917) 555-8900.

CC: IT Manager David Kim (david.kim@techcorp.io)`,
  },
  {
    name: "Shared PII Test (John Smith)",
    text: `This sample contains the same person twice to test consistent substitution.

First mention: John Smith works at the company.
Second mention: Please contact John Smith for details.

Both instances of "John Smith" should be replaced with the SAME substitute value.`,
  },
  {
    name: "IP Address Test (Private/Public)",
    text: `Network Security Log:

Internal servers (private IPs - replaced with private):
- Database server: 192.168.1.100
- App server: 10.0.0.50
- Dev machine: 172.16.0.25
- Host with CIDR: 192.168.10.50/24 (IP replaced, /24 preserved)

External connections (public IPs - replaced with public):
- Suspicious login from: 203.0.113.42
- API request from: 45.33.32.156
- Public host with CIDR: 8.8.8.8/32

Network ranges (replaced with same type, prefix preserved):
- Private network: 192.168.1.0/24 (becomes different private /24)
- Public network: 203.0.113.0/24 (becomes different public /24)

Contact: admin@example.com for issues.`,
  },
  {
    name: "Street Address Test",
    text: `Delivery Information:

Ship to: John Smith
Address: 123 Main Street
City: San Francisco, CA 94102

Alternative addresses:
- Office: 456 Oak Avenue, Suite 200
- Warehouse: 789 Industrial Blvd
- Home: 321 Pine Road, Apt 4B

Contact: john.smith@example.com
Phone: (555) 123-4567`,
  },
];

// Entity type colors for highlighting
const ENTITY_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  PERSON: { bg: "bg-blue-100", border: "border-blue-300", text: "text-blue-800" },
  EMAIL_ADDRESS: { bg: "bg-green-100", border: "border-green-300", text: "text-green-800" },
  PHONE_NUMBER: { bg: "bg-purple-100", border: "border-purple-300", text: "text-purple-800" },
  CREDIT_CARD: { bg: "bg-red-100", border: "border-red-300", text: "text-red-800" },
  US_SSN: { bg: "bg-orange-100", border: "border-orange-300", text: "text-orange-800" },
  IP_ADDRESS: { bg: "bg-cyan-100", border: "border-cyan-300", text: "text-cyan-800" },
  LOCATION: { bg: "bg-amber-100", border: "border-amber-300", text: "text-amber-800" },
  STREET_ADDRESS: { bg: "bg-teal-100", border: "border-teal-300", text: "text-teal-800" },
  DATE_TIME: { bg: "bg-pink-100", border: "border-pink-300", text: "text-pink-800" },
};

const DEFAULT_COLOR = { bg: "bg-gray-100", border: "border-gray-300", text: "text-gray-800" };

interface SubstitutionWithOriginal extends Substitution {
  original: string;
}

interface HighlightedTextProps {
  text: string;
  substitutions: SubstitutionWithOriginal[];
  showOriginal: boolean; // true for input (show original, tooltip shows substitute), false for output
}

function HighlightedText({ text, substitutions, showOriginal }: HighlightedTextProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  // Sort substitutions by position
  const sortedSubs = useMemo(
    () => [...substitutions].sort((a, b) => a.start - b.start),
    [substitutions]
  );

  // Calculate output positions (they shift because substitutes may have different lengths)
  const outputPositions = useMemo(() => {
    if (showOriginal) return sortedSubs.map((s) => ({ start: s.start, end: s.end }));

    let offset = 0;
    return sortedSubs.map((sub) => {
      const start = sub.start + offset;
      const end = start + sub.substitute.length;
      offset += sub.substitute.length - sub.original_length;
      return { start, end };
    });
  }, [sortedSubs, showOriginal]);

  // Build segments
  const segments: { text: string; subIdx: number | null }[] = [];
  let lastEnd = 0;

  outputPositions.forEach((pos, idx) => {
    if (pos.start > lastEnd) {
      segments.push({ text: text.slice(lastEnd, pos.start), subIdx: null });
    }
    segments.push({ text: text.slice(pos.start, pos.end), subIdx: idx });
    lastEnd = pos.end;
  });

  if (lastEnd < text.length) {
    segments.push({ text: text.slice(lastEnd), subIdx: null });
  }

  return (
    <div className="font-mono text-sm whitespace-pre-wrap">
      {segments.map((seg, i) => {
        if (seg.subIdx === null) {
          return <span key={i}>{seg.text}</span>;
        }

        const sub = sortedSubs[seg.subIdx];
        const colors = ENTITY_COLORS[sub.entity_type] || DEFAULT_COLOR;
        const isHovered = hoveredIdx === seg.subIdx;

        return (
          <span
            key={i}
            className={`relative inline border-b-2 ${colors.bg} ${colors.border} ${colors.text} cursor-help transition-all ${
              isHovered ? "ring-2 ring-primary-400" : ""
            }`}
            onMouseEnter={() => setHoveredIdx(seg.subIdx)}
            onMouseLeave={() => setHoveredIdx(null)}
          >
            {seg.text}
            {isHovered && (
              <span className="absolute z-10 bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg whitespace-nowrap">
                <span className="block text-gray-400 text-[10px] uppercase tracking-wide mb-1">
                  {sub.entity_type}
                </span>
                {showOriginal ? (
                  <>
                    <span className="text-red-300 line-through">{sub.original}</span>
                    <span className="mx-1">→</span>
                    <span className="text-green-300">{sub.substitute}</span>
                  </>
                ) : (
                  <>
                    <span className="text-red-300 line-through">{sub.original}</span>
                    <span className="mx-1">→</span>
                    <span className="text-green-300">{sub.substitute}</span>
                  </>
                )}
                <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-900" />
              </span>
            )}
          </span>
        );
      })}
    </div>
  );
}

export function AnonymizePage() {
  const [inputText, setInputText] = useState("");
  const [processedInput, setProcessedInput] = useState(""); // Store the input that was processed
  const [result, setResult] = useState<AnonymizeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSample, setSelectedSample] = useState("");

  // Compute substitutions with original values
  const substitutionsWithOriginals: SubstitutionWithOriginal[] = useMemo(() => {
    if (!result || !processedInput) return [];
    return result.substitutions.map((sub) => ({
      ...sub,
      original: processedInput.slice(sub.start, sub.end),
    }));
  }, [result, processedInput]);

  const handleAnonymize = async () => {
    if (!inputText.trim()) {
      setError("Please enter some text to anonymize");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await anonymizeText(inputText);
      setProcessedInput(inputText); // Store the input that was processed
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Anonymization failed");
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setInputText("");
    setProcessedInput("");
    setResult(null);
    setError(null);
    setSelectedSample("");
  };

  const handleSampleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const sampleName = e.target.value;
    setSelectedSample(sampleName);
    if (sampleName) {
      const sample = SAMPLE_TEXTS.find((s) => s.name === sampleName);
      if (sample) {
        setInputText(sample.text);
        setProcessedInput("");
        setResult(null);
        setError(null);
      }
    }
  };

  const copyToClipboard = async () => {
    if (result?.anonymized_text) {
      await navigator.clipboard.writeText(result.anonymized_text);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Anonymize Text</h1>
          <p className="mt-1 text-sm text-gray-500">
            Detect and replace personal information with consistent substitutes
          </p>
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
          <label className="text-sm font-medium text-gray-700">Try a sample:</label>
          <select
            value={selectedSample}
            onChange={handleSampleChange}
            className="input-field w-full sm:w-48"
          >
            <option value="">Select sample...</option>
            {SAMPLE_TEXTS.map((sample) => (
              <option key={sample.name} value={sample.name}>
                {sample.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Input/Output Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Input Text</h2>
            <span className="text-xs text-gray-500">
              {inputText.length.toLocaleString()} characters
            </span>
          </div>
          {result && processedInput === inputText ? (
            <div className="w-full h-64 px-4 py-3 border border-gray-300 rounded-lg bg-white overflow-auto">
              <HighlightedText
                text={processedInput}
                substitutions={substitutionsWithOriginals}
                showOriginal={true}
              />
            </div>
          ) : (
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isLoading}
              placeholder="Enter or paste text containing personal information..."
              className="w-full h-64 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all resize-none font-mono text-sm"
            />
          )}
          {result && (
            <p className="mt-2 text-xs text-gray-500">
              Hover over highlighted text to see substitution details
            </p>
          )}
        </div>

        {/* Output */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Anonymized Output</h2>
            {result && (
              <button
                onClick={copyToClipboard}
                className="text-sm text-primary-600 hover:text-primary-700 flex items-center space-x-1"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <span>Copy</span>
              </button>
            )}
          </div>
          <div className="w-full h-64 px-4 py-3 border border-gray-200 rounded-lg bg-gray-50 overflow-auto">
            {result ? (
              <HighlightedText
                text={result.anonymized_text}
                substitutions={substitutionsWithOriginals}
                showOriginal={false}
              />
            ) : (
              <span className="text-gray-400 font-mono text-sm">
                Anonymized text will appear here...
              </span>
            )}
          </div>
          {result && (
            <div className="mt-3 flex items-center text-sm text-gray-500">
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Processed in {result.metadata.processing_time_ms}ms
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
        <button
          onClick={handleAnonymize}
          disabled={isLoading || !inputText.trim()}
          className="btn-primary flex items-center justify-center space-x-2 w-full sm:w-auto"
        >
          {isLoading ? (
            <>
              <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>Processing...</span>
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <span>Anonymize</span>
            </>
          )}
        </button>
        <button onClick={handleClear} disabled={isLoading} className="btn-secondary w-full sm:w-auto">
          Clear
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3">
          <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Metadata */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Processing Summary</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-sm text-blue-600 font-medium">Entities Detected</p>
                <p className="text-2xl font-bold text-blue-700">{result.metadata.entities_detected}</p>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <p className="text-sm text-green-600 font-medium">Anonymized</p>
                <p className="text-2xl font-bold text-green-700">{result.metadata.entities_anonymized}</p>
              </div>
              <div className="bg-purple-50 rounded-lg p-4">
                <p className="text-sm text-purple-600 font-medium">New Mappings</p>
                <p className="text-2xl font-bold text-purple-700">{result.metadata.new_mappings_created}</p>
              </div>
              <div className="bg-amber-50 rounded-lg p-4">
                <p className="text-sm text-amber-600 font-medium">Existing Used</p>
                <p className="text-2xl font-bold text-amber-700">{result.metadata.existing_mappings_used}</p>
              </div>
            </div>
          </div>

          {/* Substitutions */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Substitutions Made</h3>
            {substitutionsWithOriginals.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-auto">
                {substitutionsWithOriginals.map((sub, idx) => {
                  const colors = ENTITY_COLORS[sub.entity_type] || DEFAULT_COLOR;
                  return (
                    <div
                      key={idx}
                      className="p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors.bg} ${colors.text}`}>
                          {sub.entity_type}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2 font-mono text-sm">
                        <span className="text-red-600 line-through bg-red-50 px-1 rounded">
                          {sub.original}
                        </span>
                        <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                        <span className="text-green-600 bg-green-50 px-1 rounded">
                          {sub.substitute}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No substitutions made</p>
            )}
          </div>
        </div>
      )}

      {/* Legend */}
      {result && result.substitutions.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Entity Type Legend</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(ENTITY_COLORS).map(([type, colors]) => (
              <span
                key={type}
                className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${colors.bg} ${colors.text} border ${colors.border}`}
              >
                {type}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
