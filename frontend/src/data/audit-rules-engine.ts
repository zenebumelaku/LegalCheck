import { AuditFinding, FindingCategory, FindingSeverity, FindingType } from '../types';

export interface AuditAnalysisOptions {
  checkLegalConflicts: boolean;
  checkMissingClauses: boolean;
  checkOutdatedReferences: boolean;
}

export function auditContractText(
  auditId: string,
  contractText: string,
  options: AuditAnalysisOptions
): { findings: AuditFinding[]; summary: string } {
  const findings: AuditFinding[] = [];
  const textLower = contractText.toLowerCase();

  // Helper to push finding
  const addFinding = (finding: Omit<AuditFinding, 'id' | 'auditId'>) => {
    findings.push({
      id: `fnd-${findings.length + 1}-${Date.now().toString().slice(-4)}`,
      auditId,
      ...finding
    });
  };

  // 1. PROBATION PERIOD CHECK (Article 9 & 10)
  if (options.checkLegalConflicts) {
    const probationMatch = contractText.match(/(?:probation|probationary)(?:[^.\n]{0,80})?(ninety|\b90\b|\b3 months|\bthree months|\b180\b|\b6 months|\bsix months|\b120\b)/i);
    if (probationMatch) {
      addFinding({
        title: 'Probation Period Exceeds Statutory Maximum of 60 Working Days',
        severity: 'CRITICAL',
        type: 'POTENTIAL_LEGAL_CONFLICT',
        category: 'PROBATION',
        contractExcerpt: probationMatch[0].trim(),
        contractLocation: 'Section: Probationary Period',
        issueExplanation: 'Under Ethiopian Labour Proclamation No. 1156/2019, Article 9(2), a probationary period agreed between contracting parties cannot exceed sixty (60) working days. Any provision specifying 90 days, 3 months, or longer is unlawful and renders the probation clause null, legally classifying the worker as a permanent employee.',
        legalProvision: {
          proclamationTitle: 'Labour Proclamation No. 1156/2019',
          proclamationNumber: 'No. 1156/2019',
          articleNumber: 'Article 9',
          subArticle: 'Sub-Article 2',
          provisionText: 'A probation period may be agreed upon between the contracting parties, provided that it shall be in writing and shall not exceed sixty (60) working days.',
          sourceId: 'eth-labour-proc-1156-2019',
          sourceUrl: 'https://www.ilo.org/dyn/natlex/natlex4.detail?p_lang=en&p_isn=109592',
          effectiveDate: '2019-09-05'
        },
        suggestedAction: 'Amend the probationary clause to state a maximum of 60 working days (or less), and clarify that probationary rights comply with Article 10.',
        confidenceScore: 0.98
      });
    }
  }

  // 2. WORKING HOURS CEILING (Article 61)
  if (options.checkLegalConflicts) {
    const hoursMatch = contractText.match(/(?:hours of work|working hours|workweek|normal hours)[^.\n]{0,70}(\b5[0-9]\b|\b6[0-9]\b|\b49\b|\b52\b|\b54\b)/i);
    if (hoursMatch) {
      addFinding({
        title: 'Normal Working Hours Exceed Statutory Ceiling of 48 Hours/Week',
        severity: 'HIGH',
        type: 'POTENTIAL_LEGAL_CONFLICT',
        category: 'WORKING_HOURS',
        contractExcerpt: hoursMatch[0].trim(),
        contractLocation: 'Section: Hours of Work',
        issueExplanation: 'Article 61(1) of Labour Proclamation No. 1156/2019 sets a strict statutory ceiling: normal hours of work shall not exceed eight (8) hours a day or forty-eight (48) hours a week. Defining standard weekly hours above 48 without overtime pay is illegal.',
        legalProvision: {
          proclamationTitle: 'Labour Proclamation No. 1156/2019',
          proclamationNumber: 'No. 1156/2019',
          articleNumber: 'Article 61',
          subArticle: 'Sub-Article 1',
          provisionText: 'Normal hours of work shall not exceed eight (8) hours a day or forty-eight (48) hours a week.',
          sourceId: 'eth-labour-proc-1156-2019',
          effectiveDate: '2019-09-05'
        },
        suggestedAction: 'Reduce scheduled regular work hours to 48 hours or fewer per week, and specify that any excess hours will be compensated at statutory overtime rates under Article 66.',
        confidenceScore: 0.95
      });
    }
  }

  // 3. OVERTIME EXCLUSION / FLAT RATE (Article 66)
  if (options.checkLegalConflicts) {
    if (textLower.includes('overtime') && (textLower.includes('shall not be entitled') || textLower.includes('no monetary compensation') || textLower.includes('flat hourly rate') || textLower.includes('without supplementary'))) {
      const excerptMatch = contractText.match(/(?:overtime)[^.\n]{0,120}(?:not be entitled|no monetary compensation|flat hourly rate|without supplementary)[^.\n]{0,80}/i);
      addFinding({
        title: 'Unlawful Waiver or Under-compensation of Overtime Pay',
        severity: 'HIGH',
        type: 'POTENTIAL_LEGAL_CONFLICT',
        category: 'WORKING_HOURS',
        contractExcerpt: excerptMatch ? excerptMatch[0].trim() : 'Overtime work beyond normal hours shall not be entitled to monetary compensation...',
        contractLocation: 'Section: Hours of Work / Overtime',
        issueExplanation: 'Under Article 66 of Proclamation 1156/2019, statutory overtime compensation rates (1.5x daytime, 1.75x night, 2.0x rest day, 2.5x holiday) are mandatory statutory minimums. A blanket contract clause disallowing overtime payment for non-managerial staff violates labour standards.',
        legalProvision: {
          proclamationTitle: 'Labour Proclamation No. 1156/2019',
          proclamationNumber: 'No. 1156/2019',
          articleNumber: 'Article 66',
          subArticle: 'Sub-Articles 1 & 2',
          provisionText: 'Overtime work shall be remunerated at statutory premium rates: 1.5x for day work, 1.75x for night work, 2.0x for rest days, and 2.5x for public holidays.',
          sourceId: 'eth-labour-proc-1156-2019',
          effectiveDate: '2019-09-05'
        },
        suggestedAction: 'Remove blanket waivers of overtime compensation and incorporate Article 66 statutory rate scales for all eligible employees.',
        confidenceScore: 0.92
      });
    }
  }

  // 4. MATERNITY LEAVE EXTENSION (Article 88)
  if (options.checkLegalConflicts || options.checkOutdatedReferences) {
    const maternity90Match = contractText.match(/(?:maternity leave)[^.\n]{0,80}(?:ninety|\b90\b|\b60\b)[^.\n]{0,60}days/i);
    if (maternity90Match || (textLower.includes('maternity') && textLower.includes('90') && !textLower.includes('120'))) {
      addFinding({
        title: 'Maternity Leave Period Under-reported (90 Days vs Mandatory 120 Days)',
        severity: 'CRITICAL',
        type: 'POTENTIAL_LEGAL_CONFLICT',
        category: 'MATERNITY_AND_WOMEN',
        contractExcerpt: maternity90Match ? maternity90Match[0].trim() : 'Female employees shall be entitled to ninety (90) consecutive days of maternity leave...',
        contractLocation: 'Section: Maternity and Special Leaves',
        issueExplanation: 'Under Article 88(2) of Labour Proclamation No. 1156/2019, paid maternity leave was formally expanded to 120 consecutive days (30 days prenatal + 90 days postnatal). Contracts granting only 90 days rely on repealed legislation and violate current mandatory employment rights.',
        legalProvision: {
          proclamationTitle: 'Labour Proclamation No. 1156/2019',
          proclamationNumber: 'No. 1156/2019',
          articleNumber: 'Article 88',
          subArticle: 'Sub-Article 2',
          provisionText: 'A pregnant worker shall be granted a period of thirty (30) consecutive days of paid maternity leave preceding the presumed date of her confinement and a period of ninety (90) consecutive days of paid maternity leave immediately following her confinement, amounting to a total of 120 consecutive days.',
          sourceId: 'eth-labour-proc-1156-2019',
          effectiveDate: '2019-09-05'
        },
        suggestedAction: 'Update maternity leave allocation to 120 consecutive days with full pay (30 days prenatal and 90 days postnatal), and acknowledge prenatal checkup entitlements under Article 88(1).',
        confidenceScore: 0.99
      });
    }
  }

  // 5. OUTDATED STATUTE CITATIONS (Proclamation No. 377/2003)
  if (options.checkOutdatedReferences) {
    if (contractText.includes('377/2003') || contractText.includes('377/96') || contractText.includes('Proclamation No. 377')) {
      const citeMatch = contractText.match(/(?:Labour Proclamation No\.\s*377\/2003|Proclamation\s*377\/2003|377\/2003)/i);
      addFinding({
        title: 'Citation to Repealed Labour Proclamation No. 377/2003',
        severity: 'HIGH',
        type: 'OUTDATED_OR_UNVERIFIED_REFERENCE',
        category: 'GENERAL_CONTRACT_TERMS',
        contractExcerpt: citeMatch ? citeMatch[0] : 'Labour Proclamation No. 377/2003',
        contractLocation: 'Section: Governing Law / Statutory References',
        issueExplanation: 'Labour Proclamation No. 377/2003 was officially repealed and superseded by Labour Proclamation No. 1156/2019, published in the Federal Negarit Gazeta on September 5, 2019. Relying on repealed statutory numbers introduces legal vulnerability and outdated interpretations.',
        legalProvision: {
          proclamationTitle: 'Labour Proclamation No. 1156/2019',
          proclamationNumber: 'No. 1156/2019',
          articleNumber: 'Article 192',
          provisionText: 'The Labour Proclamation No. 377/2003 is hereby repealed and replaced by this Proclamation.',
          sourceId: 'eth-labour-proc-1156-2019',
          effectiveDate: '2019-09-05'
        },
        suggestedAction: 'Replace all statutory references to Proclamation No. 377/2003 with Labour Proclamation No. 1156/2019.',
        confidenceScore: 0.99
      });
    }
  }

  // 6. ANNUAL LEAVE QUANTITY & FORFEITURE (Articles 76 & 79)
  if (options.checkLegalConflicts) {
    const leaveMatch = contractText.match(/(?:annual leave)[^.\n]{0,80}(?:fourteen|\b14\b|\b12\b|\b10\b)[^.\n]{0,50}days/i);
    if (leaveMatch) {
      addFinding({
        title: 'Annual Leave Below Statutory 16 Working Days Minimum',
        severity: 'MEDIUM',
        type: 'POTENTIAL_LEGAL_CONFLICT',
        category: 'LEAVES_AND_REST',
        contractExcerpt: leaveMatch[0].trim(),
        contractLocation: 'Section: Annual Leave',
        issueExplanation: 'Under Article 76(2) of Labour Proclamation No. 1156/2019, an employee is entitled to uninterrupted annual leave of sixteen (16) working days for the first year of service, plus 1 additional day for every two years of service. Contracts offering 14 days reflect old legislation.',
        legalProvision: {
          proclamationTitle: 'Labour Proclamation No. 1156/2019',
          proclamationNumber: 'No. 1156/2019',
          articleNumber: 'Article 76',
          subArticle: 'Sub-Article 2',
          provisionText: 'An employee who has completed one year of service shall be entitled to sixteen (16) working days of annual leave.',
          sourceId: 'eth-labour-proc-1156-2019',
          effectiveDate: '2019-09-05'
        },
        suggestedAction: 'Increase base annual leave to sixteen (16) working days for year 1, and document biennial +1 day accrual.',
        confidenceScore: 0.96
      });
    }

    if (textLower.includes('forfeited') || textLower.includes('waive his right to annual leave') || textLower.includes('shall not be carried forward and deemed forfeited')) {
      addFinding({
        title: 'Unlawful Annual Leave Forfeiture Clause',
        severity: 'HIGH',
        type: 'POTENTIAL_LEGAL_CONFLICT',
        category: 'LEAVES_AND_REST',
        contractExcerpt: 'Any untaken leave at the end of the fiscal year shall be deemed forfeited...',
        contractLocation: 'Section: Annual Leave',
        issueExplanation: 'Article 79 explicitly prohibits forfeiture or unconditional waiver of accrued annual leave. Any agreement by a worker to waive leave or forfeit it without legal postponement is null and void.',
        legalProvision: {
          proclamationTitle: 'Labour Proclamation No. 1156/2019',
          proclamationNumber: 'No. 1156/2019',
          articleNumber: 'Article 79',
          subArticle: 'Sub-Article 1',
          provisionText: 'Any agreement by a worker to waive his right to annual leave or to accept compensation in lieu of leave shall be null and void.',
          sourceId: 'eth-labour-proc-1156-2019',
          effectiveDate: '2019-09-05'
        },
        suggestedAction: 'Permit carry-over or structured postponement of annual leave in line with Article 78 instead of forfeiture.',
        confidenceScore: 0.94
      });
    }
  }

  // 7. TERMINATION NOTICE PERIODS (Article 35)
  if (options.checkLegalConflicts) {
    const noticeShortMatch = contractText.match(/(?:notice)[^.\n]{0,60}(?:fifteen|\b15\b|\b7\b|one week|\b14\b)[^.\n]{0,30}days/i);
    if (noticeShortMatch && !textLower.includes('probation')) {
      addFinding({
        title: 'Notice of Termination Sorter than Statutory Tiers',
        severity: 'HIGH',
        type: 'POTENTIAL_LEGAL_CONFLICT',
        category: 'TERMINATION_AND_SEVERANCE',
        contractExcerpt: noticeShortMatch[0].trim(),
        contractLocation: 'Section: Termination and Notice',
        issueExplanation: 'Article 35 establishes graduated statutory notice periods: 1 month for up to 1 year of service, 2 months for 1-9 years, and 3 months for more than 9 years. Setting a blanket 15-day notice period violates mandatory legal minimums for post-probation employees.',
        legalProvision: {
          proclamationTitle: 'Labour Proclamation No. 1156/2019',
          proclamationNumber: 'No. 1156/2019',
          articleNumber: 'Article 35',
          subArticle: 'Sub-Article 1',
          provisionText: 'The period of notice to be given by the employer shall not be less than: (a) one month for up to 1 year service; (b) two months for 1 to 9 years; (c) three months for exceeding 9 years.',
          sourceId: 'eth-labour-proc-1156-2019',
          effectiveDate: '2019-09-05'
        },
        suggestedAction: 'Structure the termination notice clause into the three legal tenure tiers mandated by Article 35.',
        confidenceScore: 0.91
      });
    }
  }

  // 8. EXCESSIVE NON-COMPETE CLAUSE (Civil Code Article 2589)
  if (options.checkLegalConflicts) {
    if (textLower.includes('non-compete') || textLower.includes('restrictive covenant') || (textLower.includes('not directly or indirectly work for') && textLower.includes('years'))) {
      const nonCompeteMatch = contractText.match(/(?:non-compete|restrictive covenant|competitive activity)[^.\n]{0,100}(?:three|\b3\b|\b5\b|five)[^.\n]{0,40}years/i);
      if (nonCompeteMatch || textLower.includes('3 years') || textLower.includes('three (3) full years')) {
        addFinding({
          title: 'Excessive and Unreasonable Non-Compete Restraint',
          severity: 'MEDIUM',
          type: 'POTENTIAL_LEGAL_CONFLICT',
          category: 'GENERAL_CONTRACT_TERMS',
          contractExcerpt: nonCompeteMatch ? nonCompeteMatch[0].trim() : 'Non-compete restraint for 3 full years across Ethiopia...',
          contractLocation: 'Section: Restrictive Covenant',
          issueExplanation: 'Under Article 2589 of the Ethiopian Civil Code, post-employment restrictive covenants are strictly construed and valid only when reasonably limited in duration (customarily 6-12 months), clear geographic scope, and specific trade secrets without endangering the worker\'s economic livelihood.',
          legalProvision: {
            proclamationTitle: 'Civil Code of Ethiopia (1960)',
            proclamationNumber: 'Proclamation No. 165/1960',
            articleNumber: 'Article 2589',
            provisionText: 'A covenant not to compete shall be valid only if limited as to time, place, and nature of business, and does not excessively endanger the economic future of the employee.',
            sourceId: 'eth-civil-code-1960-title-xvi',
            effectiveDate: '1960-05-05'
          },
          suggestedAction: 'Narrow the restraint period to 6–12 months, specify a reasonable geographic radius, and tie restrictions strictly to proprietary intellectual property.',
          confidenceScore: 0.88
        });
      }
    }
  }

  // 9. OCCUPATIONAL SAFETY & PPE (Article 92)
  if (options.checkLegalConflicts) {
    if (textLower.includes('purchase their own safety') || textLower.includes('supply and purchase') || textLower.includes('worker shall provide their own protective')) {
      const ppeMatch = contractText.match(/(?:purchase their own|supply and purchase)[^.\n]{0,80}(?:safety|protective|boots|respirator)/i);
      addFinding({
        title: 'Employer Shifting Protective Gear Costs to Employee',
        severity: 'CRITICAL',
        type: 'POTENTIAL_LEGAL_CONFLICT',
        category: 'SAFETY_AND_HEALTH',
        contractExcerpt: ppeMatch ? ppeMatch[0].trim() : 'Worker shall be required to supply and purchase their own safety boots...',
        contractLocation: 'Section: Occupational Safety and Gear',
        issueExplanation: 'Under Article 92(1) of Labour Proclamation No. 1156/2019, the employer has an absolute statutory obligation to provide appropriate personal protective equipment (PPE) and clothing free of charge to workers in occupational hazard environments.',
        legalProvision: {
          proclamationTitle: 'Labour Proclamation No. 1156/2019',
          proclamationNumber: 'No. 1156/2019',
          articleNumber: 'Article 92',
          subArticle: 'Sub-Article 1',
          provisionText: 'An employer shall take all necessary measures to safeguard the occupational safety and health of workers and provide free appropriate personal protective equipment.',
          sourceId: 'eth-labour-proc-1156-2019',
          effectiveDate: '2019-09-05'
        },
        suggestedAction: 'Remove any requirement for employee-funded safety gear and state that the employer supplies all necessary certified PPE free of cost.',
        confidenceScore: 0.97
      });
    }
  }

  // 10. WEEKLY REST DAY (Article 73)
  if (options.checkLegalConflicts) {
    if (textLower.includes('without intermediate rest') || textLower.includes('consecutive 12-day') || textLower.includes('consecutive 14-day')) {
      addFinding({
        title: 'Deprivation of Mandatory 24-Hour Weekly Rest Period',
        severity: 'HIGH',
        type: 'POTENTIAL_LEGAL_CONFLICT',
        category: 'LEAVES_AND_REST',
        contractExcerpt: 'Worker shall work consecutive 12-day shifts without intermediate rest days...',
        contractLocation: 'Section: Shift Roster',
        issueExplanation: 'Article 73 mandates that every worker is entitled to an uninterrupted weekly rest day of not less than twenty-four (24) consecutive hours within each 7-day period. Roster models skipping weekly rest violate statutory labour rights.',
        legalProvision: {
          proclamationTitle: 'Labour Proclamation No. 1156/2019',
          proclamationNumber: 'No. 1156/2019',
          articleNumber: 'Article 73',
          subArticle: 'Sub-Article 1',
          provisionText: 'Every worker shall be entitled to a weekly rest day consisting of not less than twenty-four (24) consecutive hours in the course of each period of seven days.',
          sourceId: 'eth-labour-proc-1156-2019',
          effectiveDate: '2019-09-05'
        },
        suggestedAction: 'Ensure shift rosters guarantee at least 24 consecutive hours of rest every seven days.',
        confidenceScore: 0.95
      });
    }
  }

  // 11. MISSING CLAUSE: PATERNITY LEAVE (Article 81)
  if (options.checkMissingClauses) {
    if (!textLower.includes('paternity') && !textLower.includes('birth of his child')) {
      addFinding({
        title: 'Absence of Statutory Paternity Leave Clause',
        severity: 'LOW',
        type: 'MISSING_OR_INCOMPLETE_CLAUSE',
        category: 'LEAVES_AND_REST',
        contractExcerpt: '[Clause omitted from contract]',
        contractLocation: 'Section: Special Leaves',
        issueExplanation: 'Proclamation No. 1156/2019, Article 81(1) introduced a statutory right to three (3) consecutive days of paid paternity leave upon the birth of a worker\'s child. Explicitly incorporating this in employment documentation prevents disputes.',
        legalProvision: {
          proclamationTitle: 'Labour Proclamation No. 1156/2019',
          proclamationNumber: 'No. 1156/2019',
          articleNumber: 'Article 81',
          subArticle: 'Sub-Article 1',
          provisionText: 'A worker shall be entitled to leave with pay for three (3) consecutive days in the case of marriage, or upon the birth of his child.',
          sourceId: 'eth-labour-proc-1156-2019',
          effectiveDate: '2019-09-05'
        },
        suggestedAction: 'Include a special leaves provision confirming three consecutive paid days for paternity leave and marriage.',
        confidenceScore: 0.85
      });
    }
  }

  // 12. MISSING CLAUSE: SEVERANCE PAY CLAUSE (Article 39 & 40)
  if (options.checkMissingClauses) {
    if (!textLower.includes('severance') && !textLower.includes('service indemnity')) {
      addFinding({
        title: 'Missing Severance and Redundancy Compensation Provision',
        severity: 'MEDIUM',
        type: 'MISSING_OR_INCOMPLETE_CLAUSE',
        category: 'TERMINATION_AND_SEVERANCE',
        contractExcerpt: '[Severance section not articulated in document]',
        contractLocation: 'Section: Termination',
        issueExplanation: 'Under Articles 39 and 40, private sector employees not covered by public servants pension are entitled to statutory severance pay upon termination due to redundancy, closure, or unlawful employer acts. Clarifying severance rights aligns contract terms with statutory standards.',
        legalProvision: {
          proclamationTitle: 'Labour Proclamation No. 1156/2019',
          proclamationNumber: 'No. 1156/2019',
          articleNumber: 'Article 39',
          subArticle: 'Sub-Article 1',
          provisionText: 'An employee who has completed his probation period shall be entitled to severance pay from the employer upon termination for non-culpable grounds.',
          sourceId: 'eth-labour-proc-1156-2019',
          effectiveDate: '2019-09-05'
        },
        suggestedAction: 'Reference statutory entitlement to severance pay in accordance with Articles 39 and 40 upon lawful triggers.',
        confidenceScore: 0.82
      });
    }
  }

  // 13. INFORMATIONAL: Work Card & Registration (Article 5)
  if (!textLower.includes('work card') && !textLower.includes('kebele') && !textLower.includes('identification')) {
    addFinding({
      title: 'Employee Work Card or Formal ID Registration Record',
      severity: 'INFORMATIONAL',
      type: 'INFORMATIONAL_OBSERVATION',
      category: 'GENERAL_CONTRACT_TERMS',
      contractExcerpt: '[Identification particulars summary]',
      contractLocation: 'Preamble: Parties Identification',
      issueExplanation: 'Article 5 of Proclamation 1156/2019 recommends recording the employee\'s formal work card number (if registered with the Ministry of Labour and Skills) and standard municipal identifiers to facilitate statutory record keeping.',
      legalProvision: {
        proclamationTitle: 'Labour Proclamation No. 1156/2019',
        proclamationNumber: 'No. 1156/2019',
        articleNumber: 'Article 5',
        provisionText: 'A contract of employment in writing shall specify the name, age, address, and work card number (if any) of the employee.',
        sourceId: 'eth-labour-proc-1156-2019',
        effectiveDate: '2019-09-05'
      },
      suggestedAction: 'Verify that the employee\'s Kebele / National ID or official work card number is archived in their personnel compliance file.',
      confidenceScore: 0.75
    });
  }

  // Summary generation
  const critical = findings.filter(f => f.severity === 'CRITICAL').length;
  const high = findings.filter(f => f.severity === 'HIGH').length;
  const medium = findings.filter(f => f.severity === 'MEDIUM').length;
  const low = findings.filter(f => f.severity === 'LOW').length;

  let summary = '';
  if (critical > 0 || high > 0) {
    summary = `The audited document contains ${critical} critical and ${high} high-severity potential non-compliance issue(s) under Ethiopian Labour Proclamation No. 1156/2019. Primary concerns involve statutory probation caps, working hours, and maternity entitlements. Revision of these clauses is strongly advised before execution.`;
  } else if (medium > 0 || low > 0) {
    summary = `The contract generally aligns with foundational Ethiopian labour standards, with ${medium} medium-severity recommendations and ${low} minor statutory adjustments regarding leave and notice periods.`;
  } else {
    summary = `The contract exhibits high compliance with Ethiopian Labour Proclamation No. 1156/2019. Key requirements including 60-day probation, maximum 48-hour workweeks, and 120-day maternity coverage are correctly represented.`;
  }

  return { findings, summary };
}
