const now = () => new Date().toISOString()

const docs = [
  {
    id: '1',
    filename: 'invoice_tcs_march.pdf',
    type: 'Invoice',
    status: 'EXTRACTED',
    confidence: 91,
    pageCount: 2,
    uploadedAt: now(),
    extractedFields: {
      INVOICE_NO: 'TCS/INV/2026/0312',
      DATE: '12/03/2026',
      VENDOR: 'Tata Consultancy Services',
      TOTAL: '₹1,24,500.00',
    },
    tables: [
      {
        id: 't1',
        headers: ['S. No', 'Description', 'Qty', 'Rate', 'Amount'],
        rows: [
          ['1', 'Consulting services', '1', '₹1,00,000', '₹1,00,000'],
          ['2', 'GST 18%', '1', '₹22,500', '₹22,500'],
        ],
      },
    ],
    bboxes: [
      { field: 'INVOICE_NO', x: 10, y: 5, width: 30, height: 6, confidence: 98 },
      { field: 'DATE', x: 72, y: 5, width: 18, height: 6, confidence: 95 },
      { field: 'TOTAL', x: 68, y: 80, width: 28, height: 8, confidence: 90 },
    ],
  },
  {
    id: '2', filename: 'reliance_receipt_01.jpg', type: 'Receipt', status: 'NEEDS_REVIEW', confidence: 74, pageCount: 1, uploadedAt: now(),
    extractedFields: { RECEIPT_NO: 'RR/2026/004', DATE: '01/04/2026', VENDOR: 'Reliance Retail', TOTAL: '₹2,450.00' },
    tables: [],
    bboxes: [{ field: 'TOTAL', x: 60, y: 70, width: 30, height: 8, confidence: 72 }],
  },
  { id: '3', filename: 'infosys_businesscard.png', type: 'Business Card', status: 'EXTRACTED', confidence: 88, pageCount: 1, uploadedAt: now(),
    extractedFields: { NAME: 'Amit Sharma', COMPANY: 'Infosys Ltd', EMAIL: 'amit.sharma@infosys.com' }, tables: [], bboxes: [{ field: 'NAME', x: 12, y: 30, width: 40, height: 6, confidence: 92 }] },
  { id: '4', filename: 'employee_id_rahul.jpg', type: 'ID Card', status: 'EXTRACTED', confidence: 85, pageCount: 1, uploadedAt: now(), extractedFields: { NAME: 'Rahul Verma', ID: 'INF-4521' }, tables: [], bboxes: [{ field: 'ID', x: 70, y: 20, width: 18, height: 8, confidence: 88 }] },
  { id: '5', filename: 'contract_keystone.pdf', type: 'Contract', status: 'PROCESSING', confidence: 0, pageCount: 5, uploadedAt: now(), extractedFields: {}, tables: [], bboxes: [] },
  { id: '6', filename: 'handwritten_note_01.jpg', type: 'Handwritten', status: 'QUEUED', confidence: 0, pageCount: 1, uploadedAt: now(), extractedFields: {}, tables: [], bboxes: [] },
  { id: '7', filename: 'invoice_smallbiz.pdf', type: 'Invoice', status: 'EXTRACTED', confidence: 79, pageCount: 1, uploadedAt: now(), extractedFields: { TOTAL: '₹7,250.00' }, tables: [], bboxes: [{ field: 'TOTAL', x: 70, y: 82, width: 22, height: 6, confidence: 79 }] },
  { id: '8', filename: 'receipt_local_market.jpg', type: 'Receipt', status: 'EXTRACTED', confidence: 82, pageCount: 1, uploadedAt: now(), extractedFields: { TOTAL: '₹420.00' }, tables: [], bboxes: [{ field: 'TOTAL', x: 62, y: 75, width: 20, height: 6, confidence: 82 }] },
  { id: '9', filename: 'nda_contract_abcd.pdf', type: 'Contract', status: 'NEEDS_REVIEW', confidence: 68, pageCount: 3, uploadedAt: now(), extractedFields: {}, tables: [], bboxes: [] },
  { id: '10', filename: 'form_onboarding.pdf', type: 'Form', status: 'EXTRACTED', confidence: 90, pageCount: 1, uploadedAt: now(), extractedFields: { EMPLOYEE: 'Sushmita Rao' }, tables: [], bboxes: [{ field: 'EMPLOYEE', x: 20, y: 30, width: 40, height: 6, confidence: 90 }] },
  { id: '11', filename: 'handwritten_notes_02.jpg', type: 'Handwritten', status: 'QUEUED', confidence: 0, pageCount: 1, uploadedAt: now(), extractedFields: {}, tables: [], bboxes: [] },
  { id: '12', filename: 'report_q1_2026.pdf', type: 'Report', status: 'EXTRACTED', confidence: 93, pageCount: 12, uploadedAt: now(), extractedFields: { TITLE: 'Q1 Financials' }, tables: [], bboxes: [] },
]

const batch = {
  id: 'batch-1',
  name: 'Batch 2026-05-25',
  total: 20,
  processed: 12,
  needsReview: 4,
  failed: 1,
  status: 'queued',
  document_ids: docs.slice(0, 8).map((d) => d.id),
  documents: docs.slice(0, 8).map((d, i) => ({ ...d, batchIndex: i })),
}

const batches = [
  batch,
  {
    id: 'batch-2',
    name: 'Batch 2026-05-24',
    total: 14,
    processed: 14,
    needsReview: 2,
    failed: 0,
    status: 'done',
    document_ids: docs.slice(4, 10).map((d) => d.id),
    documents: docs.slice(4, 10).map((d, i) => ({ ...d, batchIndex: i })),
  },
  {
    id: 'batch-3',
    name: 'Batch 2026-05-23',
    total: 9,
    processed: 7,
    needsReview: 1,
    failed: 1,
    status: 'failed',
    document_ids: docs.slice(2, 9).map((d) => d.id),
    documents: docs.slice(2, 9).map((d, i) => ({ ...d, batchIndex: i })),
  },
]

export default {
  documents: docs,
  batch,
  batches,
}
