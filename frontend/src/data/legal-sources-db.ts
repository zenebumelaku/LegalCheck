import { LegalSource } from '../types';

export const ETHIOPIAN_LEGAL_SOURCES: LegalSource[] = [
  {
    id: 'eth-labour-proc-1156-2019',
    proclamationNumber: 'No. 1156/2019',
    title: 'Labour Proclamation No. 1156/2019',
    officialGazeta: 'Federal Negarit Gazeta, 25th Year No. 89',
    publicationDate: '2019-09-05',
    effectiveDate: '2019-09-05',
    status: 'IN_FORCE',
    category: 'Employment & Labour Law',
    description: 'The primary legislation governing employment relations, working conditions, contracts of employment, collective bargaining, and occupational safety in Ethiopia. Repeals Proclamation No. 377/2003.',
    sourceUrl: 'https://www.ilo.org/dyn/natlex/natlex4.detail?p_lang=en&p_isn=109592',
    articlesCount: 193,
    provenance: {
      publisher: 'House of Peoples Representatives of the Federal Democratic Republic of Ethiopia',
      verifiedBy: 'Ethiopian Legal Documentation Service',
      lastVerifiedDate: '2026-01-15',
      gazetaVolume: 'Year 25, No. 89, Addis Ababa'
    },
    articles: [
      {
        id: 'art-4',
        articleNumber: 'Article 4',
        title: 'Elements of a Contract of Employment',
        text: 'A contract of employment shall be deemed formed where a person agrees directly or indirectly to perform work for and under the authority of an employer for a specified or unspecified period or for piece work in return for wages.',
        amharicText: 'አንድ ሰው በቀጥታም ሆነ በተዘዋዋሪ መንገድ ደመወዝ እየተከፈለው በአሰሪው መሪነት ለተወሰነ ወይም ላልተወሰነ ጊዜ ወይም ለተወሰነ ሥራ ለመስራት የተስማማ እንደሆነ የስራ ውል እንደተደረገ ይቆጠራል።',
        notes: 'Mandatory definition of employer-employee relationship under Ethiopian jurisdiction.'
      },
      {
        id: 'art-5',
        articleNumber: 'Article 5',
        title: 'Form of Contract of Employment',
        text: 'Unless otherwise provided by law, a contract of employment shall not be subject to any special form. A contract of employment may be concluded orally or in writing. Where a contract of employment is in writing, it shall specify the name and address of the employer, the name, age, address, and work card number (if any) of the employee, the nature of the employment and place of work, the wage to be paid and the method and frequency of payment, and the signatures of the contracting parties.',
        notes: 'Specifies minimum mandatory written elements of an Ethiopian employment agreement.'
      },
      {
        id: 'art-9',
        articleNumber: 'Article 9',
        title: 'Probation Period',
        subArticle: 'Sub-Articles 1 & 2',
        text: '1. A person who is employed may be tested for a probation period with a view to determining his suitability to a job position. 2. A probation period may be agreed upon between the contracting parties, provided that it shall be in writing and shall not exceed sixty (60) working days.',
        amharicText: 'የሙከራ ጊዜ በጽሑፍ ስምምነት ሊደረግበት ይችላል፤ ሆኖም ጊዜው ከስልሳ (60) የሥራ ቀናት መብለጥ የለበትም።',
        notes: 'CRITICAL LIMIT: Probation may NEVER exceed 60 working days. Probation periods extending beyond 60 working days (e.g. 90 days or 6 months) are illegal and automatically confer regular employee status.'
      },
      {
        id: 'art-10',
        articleNumber: 'Article 10',
        title: 'Effect of Probation Contract',
        subArticle: 'Sub-Articles 1 & 2',
        text: '1. Unless otherwise provided by this Proclamation, an employee on probation shall have all the rights and obligations that an employee has who has completed his probation period. 2. If the employee proves to be unfit for the post during his probation period, the employer may terminate the contract of employment without notice and without being required to pay severance pay or compensation.',
        notes: 'Guarantees standard worker rights during probation, including wage and safety.'
      },
      {
        id: 'art-11',
        articleNumber: 'Article 11',
        title: 'Contract of Employment for an Indefinite Period',
        text: 'Any contract of employment shall be deemed to have been made for an indefinite period except for those contracts provided for under Article 10(2) and Article 18 of this Proclamation. Definite term contracts are strictly restricted to temporary tasks, replacements, seasonal work, or specific project milestones.',
        notes: 'Employment contracts in Ethiopia are legally presumed indefinite unless an explicit exception under Article 18 applies.'
      },
      {
        id: 'art-27',
        articleNumber: 'Article 27',
        title: 'Termination of Contract of Employment by the Employer Without Notice',
        subArticle: 'Sub-Articles 1 & 2',
        text: 'A contract of employment may be terminated by an employer without notice only on the following grounds: repeated and unjustified tardiness or absenteeism despite warnings; deceitful or fraudulent behavior; misappropriation of property or funds; persistently unviable performance despite training; physical assault or fighting at the workplace; being intoxicated during work hours; commission of a grave offense. Prior written warnings are mandatory for tardiness and absenteeism.',
        notes: 'Strict limitation on summary dismissals. Arbitrary termination without following statutory warning steps constitutes unlawful dismissal.'
      },
      {
        id: 'art-35',
        articleNumber: 'Article 35',
        title: 'Period of Notice',
        subArticle: 'Sub-Article 1',
        text: 'The period of notice to be given by the employer shall not be less than: (a) one month for an employee who has completed his probation period and has a period of service not exceeding one year; (b) two months for an employee who has a period of service from one to nine years; (c) three months for an employee who has a period of service exceeding nine years.',
        notes: 'Mandatory statutory minimum notice periods. Contracts providing shorter notice (e.g. 15 days) are void to the extent of the deficit.'
      },
      {
        id: 'art-39',
        articleNumber: 'Article 39',
        title: 'Severance Pay',
        subArticle: 'Sub-Articles 1 & 2',
        text: 'An employee who has completed his probation period and who is not subject to the Public Servants Pension Proclamation shall be entitled to severance pay from the employer where the contract of employment is terminated due to reduction of workers, closure or bankruptcy, unlawful acts of the employer, or retirement.',
        notes: 'Severance calculation starts at thirty (30) times the average daily wage for the first year of service plus 1/3 for each subsequent year.'
      },
      {
        id: 'art-61',
        articleNumber: 'Article 61',
        title: 'Maximum Normal Hours of Work',
        subArticle: 'Sub-Articles 1 & 2',
        text: '1. Normal hours of work shall not exceed eight (8) hours a day or forty-eight (48) hours a week. 2. In this Proclamation, "normal hours of work" means the time during which the worker actually performs work or avails himself for work in accordance with the law, collective agreement, or work rules.',
        amharicText: 'መደበኛ የሥራ ሰዓት በቀን ከስምንት (8) ሰዓት ወይም በሳምንት ከአርባ ስምንት (48) ሰዓት መብለጥ የለበትም።',
        notes: 'Statutory ceiling. Employment clauses establishing standard weeks of 50+ hours without overtime compensation are non-compliant.'
      },
      {
        id: 'art-66',
        articleNumber: 'Article 66',
        title: 'Overtime Work and Compensation Rates',
        subArticle: 'Sub-Articles 1, 2 & 3',
        text: 'Overtime work shall be remunerated at the following rates: (a) In the case of work done between 6:00 a.m. and 10:00 p.m., at the rate of 1.5 times the ordinary hourly rate; (b) In the case of nighttime work between 10:00 p.m. and 6:00 a.m., at the rate of 1.75 times the ordinary hourly rate; (c) In the case of work done on a weekly rest day, at the rate of 2.0 times the ordinary hourly rate; (d) In the case of work done on a public holiday, at the rate of 2.5 times the ordinary hourly rate.',
        notes: 'Overtime calculation rates are statutory floors and cannot be waived or reduced by individual employment contracts.'
      },
      {
        id: 'art-73',
        articleNumber: 'Article 73',
        title: 'Weekly Rest Day',
        subArticle: 'Sub-Articles 1 & 2',
        text: 'Every worker shall be entitled to a weekly rest day consisting of not less than twenty-four (24) consecutive hours in the course of each period of seven days. The weekly rest day shall, as far as possible, fall on Sunday.',
        notes: 'Mandatory rest requirement. Continuous 7-day work schedules without compensatory rest are unlawful.'
      },
      {
        id: 'art-76',
        articleNumber: 'Article 76',
        title: 'Granting of Annual Leave',
        subArticle: 'Sub-Articles 1 & 2',
        text: '1. An employee shall be entitled to uninterrupted annual leave with pay. 2. An employee who has completed one year of service shall be entitled to sixteen (16) working days of annual leave. 3. For every additional two years of service, the employee shall be entitled to one (1) additional working day of annual leave.',
        amharicText: 'አንድ ዓመት ያገለገለ ሠራተኛ የአሥራ ስድስት (16) የሥራ ቀናት የዓመት ፈቃድ በሙሉ ደመወዝ የማግኘት መብት አለው።',
        notes: 'Proclamation 1156/2019 increased base annual leave from 14 days (under old Proc. 377/2003) to 16 working days.'
      },
      {
        id: 'art-79',
        articleNumber: 'Article 79',
        title: 'Prohibition of Waiving Annual Leave',
        subArticle: 'Sub-Articles 1 & 2',
        text: 'Any agreement by a worker to waive his right to annual leave or to accept compensation in lieu of leave shall be null and void. Payment in lieu of annual leave is permissible only upon termination of the contract of employment for unused accrued days.',
        notes: 'Agreements to "cash out" or forfeit accrued annual leave during active employment are void ab initio.'
      },
      {
        id: 'art-81',
        articleNumber: 'Article 81',
        title: 'Special Leaves (Paternity, Mourning, Marriage)',
        subArticle: 'Sub-Articles 1 & 2',
        text: '1. A worker shall be entitled to leave with pay for three (3) consecutive days in the case of marriage, or upon the birth of his child (paternity leave). 2. A worker shall be entitled to leave with pay for three (3) consecutive days in the event of the death of his spouse, descendant, ascendant, brother or sister.',
        notes: 'Proclamation 1156/2019 introduced formal statutory paternity leave of 3 consecutive paid days for male employees.'
      },
      {
        id: 'art-88',
        articleNumber: 'Article 88',
        title: 'Maternity Leave',
        subArticle: 'Sub-Articles 1, 2, 3 & 4',
        text: '1. An employer shall grant a pregnant worker paid leave for medical examination connected with her pregnancy upon presentation of a medical certificate. 2. A pregnant worker shall be granted a period of thirty (30) consecutive days of paid maternity leave preceding the presumed date of her confinement and a period of ninety (90) consecutive days of paid maternity leave immediately following her confinement, amounting to a total of 120 consecutive days. 3. Pregnant workers shall not be assigned to night work or overtime work from 10:00 p.m. to 6:00 a.m.',
        amharicText: 'እርጉዝ የሆነች ሠራተኛ ከወሊድ በፊት 30 ተከታታይ ቀናት እና ከወለደች በኋላ 90 ተከታታይ ቀናት በድምሩ 120 ተከታታይ ቀናት የወሊድ ፈቃድ በሙሉ ደመወዝ ይሰጣታል።',
        notes: 'Proclamation 1156/2019 expanded maternity leave to 120 consecutive paid days (previously 90 days under Proc. 377/2003). Contracts citing 90 days are outdated.'
      },
      {
        id: 'art-89',
        articleNumber: 'Article 89',
        title: 'Minimum Age for Employment',
        subArticle: 'Sub-Article 1',
        text: 'The minimum age for employment shall be fifteen (15) years. It is prohibited to employ a young worker under eighteen (18) years of age on work which is likely to jeopardize his health, safety, morals, or education.',
        notes: 'Raised minimum employment age from 14 years under old legislation to 15 years.'
      },
      {
        id: 'art-92',
        articleNumber: 'Article 92',
        title: 'Occupational Safety, Health and Working Environment',
        subArticle: 'Sub-Articles 1 & 2',
        text: 'An employer shall take all necessary measures to safeguard the occupational safety and health of workers, provide free appropriate personal protective equipment (PPE), ensure proper ventilation and lighting, and establish a workplace safety committee.',
        notes: 'Mandates employer-funded protective gear and safety procedures.'
      }
    ]
  },
  {
    id: 'eth-civil-code-1960-title-xvi',
    proclamationNumber: 'Proclamation No. 165/1960',
    title: 'Civil Code of Ethiopia (1960) - Title XVI Contracts for the Performance of Services',
    officialGazeta: 'Negarit Gazeta, Gazette Extraordinary, 19th Year No. 2',
    publicationDate: '1960-05-05',
    effectiveDate: '1960-05-05',
    status: 'AMENDED',
    category: 'Civil Law & Contracts',
    description: 'General contract principles governing professional service agreements, agency, independent contractors, and non-disclosure obligations. Labour Proclamation No. 1156/2019 takes precedence over employment matters as lex specialis.',
    sourceUrl: 'https://www.lawethiopia.com/images/civil_code.pdf',
    articlesCount: 88,
    provenance: {
      publisher: 'Empire of Ethiopia / Ministry of Justice',
      verifiedBy: 'Ethiopian Legal Documentation Service',
      lastVerifiedDate: '2026-01-15',
      gazetaVolume: 'Year 19, No. 2'
    },
    articles: [
      {
        id: 'civ-2512',
        articleNumber: 'Article 2512',
        title: 'Definition of Contract of Service',
        text: 'A contract of service is a contract whereby one of the parties, the employee, undertakes to provide to the other, the employer, his services for a specified or unspecified period or for a piece of work, in return for remuneration.',
        notes: 'Subsidiary applicability where Labour Proclamation does not provide specific coverage (e.g. managerial personnel).'
      },
      {
        id: 'civ-2589',
        articleNumber: 'Article 2589',
        title: 'Covenant not to Compete (Non-Compete Clauses)',
        text: 'A covenant whereby the employee binds himself not to engage in any competitive activity after the termination of the contract shall be valid only if: (a) it is in writing; (b) the employee has gained special knowledge of manufacturing or trade secrets; (c) the restraint is limited as to time, place, and nature of business; and (d) the restraint does not excessively endanger the economic future of the employee.',
        notes: 'Under Ethiopian jurisprudence, broad nationwide or indefinite non-compete clauses without geographic or time limits (max 1-2 years) are void.'
      }
    ]
  },
  {
    id: 'eth-commercial-reg-980-2016',
    proclamationNumber: 'No. 980/2016',
    title: 'Commercial Registration and Licensing Proclamation No. 980/2016',
    officialGazeta: 'Federal Negarit Gazeta, 22nd Year No. 101',
    publicationDate: '2016-08-05',
    effectiveDate: '2016-08-05',
    status: 'IN_FORCE',
    category: 'Commercial & Business Regulation',
    description: 'Regulates commercial entities, employer registration numbers, and statutory compliance for businesses operating in Ethiopia.',
    articlesCount: 65,
    provenance: {
      publisher: 'House of Peoples Representatives',
      verifiedBy: 'Ministry of Trade and Regional Integration',
      lastVerifiedDate: '2026-01-10',
      gazetaVolume: 'Year 22, No. 101'
    },
    articles: [
      {
        id: 'com-22',
        articleNumber: 'Article 22',
        title: 'Obligation of Commercial Entities Regarding Personnel',
        text: 'Every registered commercial business enterprise shall ensure full compliance with Ethiopian labour and employment regulations and maintain proper employee registries with the competent regulatory authorities.',
        notes: 'Sets compliance accountability on enterprise management.'
      }
    ]
  },
  {
    id: 'eth-old-proc-377-2003',
    proclamationNumber: 'No. 377/2003',
    title: 'Labour Proclamation No. 377/2003 (Repealed)',
    officialGazeta: 'Federal Negarit Gazeta, 10th Year No. 12',
    publicationDate: '2004-02-26',
    effectiveDate: '2004-02-26',
    status: 'REPEALED',
    category: 'Historical Labour Law',
    description: 'Former labour proclamation of Ethiopia. REPEALED and superseded in full by Labour Proclamation No. 1156/2019. Any modern contract citing Proclamation 377/2003 contains outdated legal references.',
    articlesCount: 191,
    provenance: {
      publisher: 'House of Peoples Representatives',
      verifiedBy: 'Ethiopian Legal Documentation Service',
      lastVerifiedDate: '2026-01-15',
      gazetaVolume: 'Year 10, No. 12 (Superseded)'
    },
    articles: [
      {
        id: 'old-proc-rep',
        articleNumber: 'Repealed Provisions',
        title: 'Status: Null and Void',
        text: 'Proclamation No. 377/2003 was formally repealed on September 5, 2019 pursuant to Article 192 of Labour Proclamation No. 1156/2019. Contracts referencing this statute must be revised.',
        notes: 'Common mistake in older Ethiopian business contract templates.'
      }
    ]
  }
];
