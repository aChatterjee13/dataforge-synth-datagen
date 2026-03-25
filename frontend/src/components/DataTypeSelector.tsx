import { FileText, Table, Zap, Database, Network, ShieldCheck, Terminal, GitBranch, Share2 } from 'lucide-react';
import { Card, CardContent } from './Card';
import { DataType } from '../types';

interface DataTypeSelectorProps {
  selectedType: DataType;
  onTypeSelect: (type: DataType) => void;
}

const dataTypes = [
  {
    type: 'structured' as DataType,
    icon: Table,
    title: 'Structured Data',
    description: 'Tabular data from CSV or Excel files',
    details: ['CTGAN, TVAE, GaussianCopula', 'TimeGAN for time-series', 'ML efficacy validation'],
    color: 'blue',
  },
  {
    type: 'unstructured' as DataType,
    icon: FileText,
    title: 'Unstructured Data',
    description: 'Documents and PDFs with GPT-powered generation',
    details: ['GPT-4 content generation', 'Style & structure preservation', 'Privacy-first synthesis'],
    color: 'purple',
  },
  {
    type: 'api_testing' as DataType,
    icon: Zap,
    title: 'API Testing',
    description: 'Generate test suites from OpenAPI/Swagger specs',
    details: ['Postman collection output', 'Positive, negative & edge cases', 'Security & relationship tests'],
    color: 'green',
  },
  {
    type: 'data_testing' as DataType,
    icon: Database,
    title: 'Data Testing',
    description: 'Generate test data from database schemas',
    details: ['SQL INSERT generation', 'Constraint violation tests', 'Multi-dialect support'],
    color: 'amber',
  },
  {
    type: 'multi_table' as unknown as DataType,
    icon: Network,
    title: 'Multi-Table',
    description: 'Multiple related tables with referential integrity',
    details: ['HMA Synthesizer', 'Foreign key preservation', 'Cross-table relationships'],
    color: 'teal',
  },
  {
    type: 'pii_masking' as DataType,
    icon: ShieldCheck,
    title: 'PII Masking',
    description: 'Auto-detect and anonymize personally identifiable information',
    details: ['Auto-detect emails, SSNs, phones', 'Synthetic replacement with Faker', 'Privacy risk assessment'],
    color: 'rose',
  },
  {
    type: 'log_synthesis' as DataType,
    icon: Terminal,
    title: 'Log & Event Data',
    description: 'Synthesize realistic log files from samples',
    details: ['Apache, nginx, syslog, JSON', 'Temporal pattern preservation', 'Configurable error rates'],
    color: 'orange',
  },
  {
    type: 'cdc_testing' as DataType,
    icon: GitBranch,
    title: 'CDC / Pipeline Testing',
    description: 'Generate CDC event streams from database schemas',
    details: ['Debezium JSON format', 'INSERT/UPDATE/DELETE sequences', 'Referential integrity'],
    color: 'cyan',
  },
  {
    type: 'graph_synthesis' as DataType,
    icon: Share2,
    title: 'Graph / Network Data',
    description: 'Synthesize graphs preserving structural properties',
    details: ['Scale-free, random, small-world', 'Degree distribution matching', 'Community preservation'],
    color: 'indigo',
  },
] as const;

const colorMap: Record<string, { border: string; bg: string; text: string; hover: string; badge: string }> = {
  blue: { border: 'border-blue-500', bg: 'bg-blue-50', text: 'text-blue-600', hover: 'hover:border-blue-300', badge: 'bg-blue-600' },
  purple: { border: 'border-purple-500', bg: 'bg-purple-50', text: 'text-purple-600', hover: 'hover:border-purple-300', badge: 'bg-purple-600' },
  green: { border: 'border-green-500', bg: 'bg-green-50', text: 'text-green-600', hover: 'hover:border-green-300', badge: 'bg-green-600' },
  amber: { border: 'border-amber-500', bg: 'bg-amber-50', text: 'text-amber-600', hover: 'hover:border-amber-300', badge: 'bg-amber-600' },
  teal: { border: 'border-teal-500', bg: 'bg-teal-50', text: 'text-teal-600', hover: 'hover:border-teal-300', badge: 'bg-teal-600' },
  rose: { border: 'border-rose-500', bg: 'bg-rose-50', text: 'text-rose-600', hover: 'hover:border-rose-300', badge: 'bg-rose-600' },
  orange: { border: 'border-orange-500', bg: 'bg-orange-50', text: 'text-orange-600', hover: 'hover:border-orange-300', badge: 'bg-orange-600' },
  cyan: { border: 'border-cyan-500', bg: 'bg-cyan-50', text: 'text-cyan-600', hover: 'hover:border-cyan-300', badge: 'bg-cyan-600' },
  indigo: { border: 'border-indigo-500', bg: 'bg-indigo-50', text: 'text-indigo-600', hover: 'hover:border-indigo-300', badge: 'bg-indigo-600' },
};

export default function DataTypeSelector({ selectedType, onTypeSelect }: DataTypeSelectorProps) {
  return (
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
      {dataTypes.map(({ type, icon: Icon, title, description, details, color }) => {
        const isSelected = selectedType === type;
        const colors = colorMap[color];

        return (
          <Card
            key={type}
            className={`cursor-pointer transition-all hover:shadow-lg ${
              isSelected
                ? `border-2 ${colors.border} shadow-lg ${colors.bg}`
                : `border-2 border-gray-200 ${colors.hover}`
            }`}
            onClick={() => onTypeSelect(type)}
          >
            <CardContent className="p-6 text-center">
              <div className={`mb-4 flex justify-center ${isSelected ? colors.text : 'text-gray-600'}`}>
                <Icon className="h-12 w-12" />
              </div>
              <h3 className="text-lg font-bold mb-2 text-gray-900">{title}</h3>
              <p className="text-sm text-gray-600 mb-3">{description}</p>
              <div className="text-xs text-gray-500 space-y-1">
                {details.map((d, i) => (
                  <div key={i}>• {d}</div>
                ))}
              </div>
              {isSelected && (
                <div className={`mt-4 px-3 py-1 ${colors.badge} text-white rounded-full text-sm font-semibold`}>
                  Selected
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
