import {
  AuditService,
  assertDemoInputIsSynthetic,
} from '../services/audit.service';

function assert(condition: boolean, message: string): void {
  if (!condition) throw new Error(`TEST FAILED: ${message}`);
  console.log(`✓ PASS: ${message}`);
}

function runTests(): void {
  console.log('\n--- Running Audit Privacy and Evidence Mapping Tests ---');

  const supported = AuditService.mapBackendFinding(
    {
      id: 'finding-1',
      category: 'potential_legal_conflict',
      severity: 'high',
      clause_id: 'clause-1',
      clause_text: 'Synthetic clause excerpt for mapping test.',
      explanation: 'Synthetic supported explanation.',
      evidence_assessment: 'supporting',
      citations: [
        {
          source_id: 'synthetic-source-id',
          source_title: 'Synthetic legal source',
          source_url: 'https://example.test/source',
          version_label: 'fixture-only',
          article_number: 'Fixture Article 7',
          sub_article_reference: '(b)',
          supporting_quote: 'Synthetic quote from fixture text.',
          relevance_information: 'Test fixture'
        }
      ]
    },
    0,
    'audit-fixture-id'
  );
  assert(supported.auditId === 'audit-fixture-id', 'Backend finding remains tied to its audit');
  assert(supported.severity === 'HIGH', 'Supported findings preserve backend priority');
  assert(supported.citations?.[0].sourceTitle === 'Synthetic legal source', 'Citation metadata comes from the backend response');
  assert(supported.legalProvision === undefined, 'Mapper does not fabricate a source or legal provision');
  assert(supported.confidenceScore === undefined, 'Mapper does not invent model confidence');

  const unsupported = AuditService.mapBackendFinding(
    {
      id: 'finding-2',
      category: 'potential_legal_conflict',
      severity: 'critical',
      clause_id: 'clause-2',
      clause_text: 'Synthetic unsupported clause.',
      explanation: 'Evidence was uncertain.',
      evidence_assessment: 'insufficient',
      citations: []
    },
    1,
    'audit-fixture-id'
  );
  assert(unsupported.severity === 'INFORMATIONAL', 'Unsupported backend output cannot display as a high-severity legal violation');
  assert(unsupported.type === 'INSUFFICIENT_EVIDENCE', 'Unsupported output is explicitly identified');
  assert(unsupported.citations?.length === 0, 'Unsupported output has no invented citation');
  assert(
    unsupported.title === 'Insufficient evidence for a legal conclusion',
    'Unsupported output is not presented as a definitive conclusion'
  );

  const missingCitation = AuditService.mapBackendFinding(
    {
      id: 'finding-3',
      severity: 'critical',
      clause_text: 'Synthetic clause without citations.',
      explanation: 'No citation returned.',
      evidence_assessment: 'supporting',
      citations: []
    },
    2,
    'audit-fixture-id'
  );
  assert(missingCitation.severity === 'INFORMATIONAL', 'A supporting label without citations is not shown as a definitive high-severity finding');
  assert(missingCitation.evidenceAssessment === 'insufficient', 'Missing citations downgrade the displayed evidence state');

  let blockedPrivateUpload = false;
  try {
    assertDemoInputIsSynthetic(true, false);
  } catch {
    blockedPrivateUpload = true;
  }
  assert(blockedPrivateUpload, 'Client-side demo mode rejects real contract uploads');
  assertDemoInputIsSynthetic(true, true);
  assertDemoInputIsSynthetic(false, false);

  console.log('--- Audit Privacy and Evidence Mapping Tests Passed ---\n');
}

runTests();
