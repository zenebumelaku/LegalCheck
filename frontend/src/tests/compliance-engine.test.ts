/**
 * Unit Tests for LegalCheck Ethiopia Compliance Engine
 * Tests Labour Proclamation No. 1156/2019 validation rules
 */

import { auditContractText } from '../data/audit-rules-engine';
import { formatBytes, formatDate, getSeverityStyles } from '../lib/utils';

function assert(condition: boolean, message: string) {
  if (!condition) {
    throw new Error(`TEST FAILED: ${message}`);
  }
  console.log(`✓ PASS: ${message}`);
}

export function runTests() {
  console.log('\n--- Running LegalCheck Ethiopia Engine Tests ---');

  // Test 1: Probation Cap (Article 9)
  const contractWithBadProbation = `
    EMPLOYMENT AGREEMENT
    2. Probation Period: The employee shall complete a probation period of 90 calendar days.
    3. Normal working hours: 40 hours per week.
  `;
  const result1 = auditContractText('test-1', contractWithBadProbation, {
    checkLegalConflicts: true,
    checkMissingClauses: false,
    checkOutdatedReferences: false
  });
  const probationFinding = result1.findings.find(f => f.category === 'PROBATION');
  assert(!!probationFinding, 'Identifies probation period exceeding statutory 60 working days');
  assert(probationFinding?.severity === 'CRITICAL', 'Probation violation is marked CRITICAL');
  assert(probationFinding?.legalProvision.articleNumber === 'Article 9', 'Cites Article 9 correctly');

  // Test 2: Maternity Leave Extension to 120 Days (Article 88)
  const contractWithOutdatedMaternity = `
    6. Maternity Leave: Female employees shall receive ninety (90) days of maternity leave with pay.
  `;
  const result2 = auditContractText('test-2', contractWithOutdatedMaternity, {
    checkLegalConflicts: true,
    checkMissingClauses: false,
    checkOutdatedReferences: false
  });
  const maternityFinding = result2.findings.find(f => f.category === 'MATERNITY_AND_WOMEN');
  assert(!!maternityFinding, 'Flags outdated 90-day maternity leave');
  assert(maternityFinding?.legalProvision.articleNumber === 'Article 88', 'Cites Article 88 correctly');

  // Test 3: Repealed Proclamation 377/2003 Citation
  const contractWithOldCite = `
    9. Governing Law: This contract is drafted under Labour Proclamation No. 377/2003.
  `;
  const result3 = auditContractText('test-3', contractWithOldCite, {
    checkLegalConflicts: false,
    checkMissingClauses: false,
    checkOutdatedReferences: true
  });
  const citeFinding = result3.findings.find(f => f.type === 'OUTDATED_OR_UNVERIFIED_REFERENCE');
  assert(!!citeFinding, 'Flags repealed Proclamation No. 377/2003 citation');

  // Test 4: Utility Formatters
  assert(formatBytes(1024) === '1 KB', 'formatBytes formats 1024 as 1 KB');
  assert(formatBytes(1048576) === '1 MB', 'formatBytes formats 1MB');

  const criticalStyles = getSeverityStyles('CRITICAL');
  assert(criticalStyles.label === 'Critical Risk', 'Severity style matches Critical Risk');

  console.log('--- All Legal Engine Tests Passed Successfully ---\n');
}

// Execute tests if executed directly
if (typeof process !== 'undefined') {
  runTests();
}
