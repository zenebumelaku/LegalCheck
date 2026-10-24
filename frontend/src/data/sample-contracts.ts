export interface SampleContract {
  id: string;
  title: string;
  organization: string;
  role: string;
  type: 'EMPLOYMENT_CONTRACT';
  language: 'ENGLISH' | 'AMHARIC' | 'MIXED';
  description: string;
  knownIssues: string[];
  content: string;
}

export const SAMPLE_ETHIOPIAN_CONTRACTS: SampleContract[] = [
  {
    id: 'sample-tech-startup',
    title: 'Senior Software Engineer Employment Contract',
    organization: 'Addis Tech Solutions PLC',
    role: 'Lead Software Architect',
    type: 'EMPLOYMENT_CONTRACT',
    language: 'ENGLISH',
    description: 'A standard tech startup contract featuring common legal pitfalls: 90-day probation, outdated proclamation 377/2003 reference, 54-hour workweek, and 90-day maternity clause.',
    knownIssues: [
      'Probation set to 90 days (Article 9 allows max 60 working days)',
      'Normal working hours set to 52 hours/week (Article 61 caps at 48 hours)',
      'Annual leave set to 14 working days (Article 76 mandates 16 days)',
      'Maternity leave set to 90 days citing Proclamation 377/2003 (Article 88 mandates 120 consecutive days)',
      'Outdated statutory citation to repealed Labour Proclamation No. 377/2003',
      'Blanket non-compete for 3 years nationwide without compensation (Civil Code Art. 2589)'
    ],
    content: `CONTRACT OF EMPLOYMENT

BETWEEN:
1. ADDIS TECH SOLUTIONS PRIVATE LIMITED COMPANY, a company duly incorporated under the commercial laws of Ethiopia, with registered head office located at Kirkos Sub-City, Addis Ababa (hereinafter referred to as the "Employer").

AND:
2. MR. DAWIT KEBEDE, Ethiopian citizen, residing in Yeka Sub-City, Addis Ababa, holding Kebele ID No. 04/99120 (hereinafter referred to as the "Employee").

IT IS HEREBY AGREED AS FOLLOWS:

1. POSITION AND COMMENCEMENT
The Employer agrees to employ the Employee as Lead Software Architect. The employment commences on 1st November 2026.

2. PROBATIONARY PERIOD
The Employee shall undergo a mandatory probation period of ninety (90) calendar days from the date of commencement. During this probation period of 90 days, either party may terminate this agreement upon 24 hours written notice without assignment of cause or severance.

3. HOURS OF WORK
The normal working hours for the Employee shall be 52 hours per week, structured as 9 hours per day from Monday to Friday, and 7 hours on Saturday mornings. In light of the executive technical nature of the position, overtime work beyond 52 hours shall not be entitled to monetary compensation.

4. REMUNERATION AND TAXATION
The Employer shall pay the Employee a monthly gross salary of ETB 85,000 (Eighty-Five Thousand Ethiopian Birr), payable at the end of each calendar month after standard deductions for Personal Income Tax and Pension Contribution in accordance with Ethiopian revenue laws.

5. ANNUAL LEAVE AND PUBLIC HOLIDAYS
The Employee shall be entitled to fourteen (14) working days of annual leave with pay upon completion of one full continuous year of service. Any untaken leave at the end of the fiscal year shall be deemed forfeited and cannot be carried forward.

6. MATERNITY AND SPECIAL LEAVES
In accordance with Ethiopian Labour Proclamation No. 377/2003, female employees shall be entitled to ninety (90) consecutive days of maternity leave (30 days prenatal and 60 days postnatal) with full pay. Paternity leave shall not be provided except at the discretion of management.

7. TERMINATION AND NOTICE
After the probation period, either party may terminate this contract by providing fifteen (15) calendar days written notice or payment of salary in lieu of notice, regardless of the Employee's length of service with the company.

8. RESTRICTIVE COVENANT / NON-COMPETE
The Employee agrees that for a period of three (3) full years following the termination of this contract for any reason, the Employee shall not directly or indirectly work for, consult with, or own any equity in any software, fintech, or technology enterprise operating anywhere in the Federal Democratic Republic of Ethiopia.

9. GOVERNING LAW
This contract is governed by and construed in accordance with the Labour Proclamation No. 377/2003 and the Civil Code of Ethiopia.`
  },
  {
    id: 'sample-factory-worker',
    title: 'Manufacturing Plant Equipment Operator Agreement',
    organization: 'Finfinne Agro-Industrial PLC',
    role: 'Heavy Machinery Plant Operator',
    type: 'EMPLOYMENT_CONTRACT',
    language: 'ENGLISH',
    description: 'Factory contract containing hazardous environment issues: shifting safety equipment costs to the worker, mandatory weekend overtime without statutory 2.0x multiplier, and arbitrary summary dismissal.',
    knownIssues: [
      'Worker required to purchase own Personal Protective Equipment (Violates Article 92)',
      'Weekend overtime remunerated at flat 1.0x rate (Article 66 mandates 2.0x)',
      'Employer claims right to terminate immediately for any verbal dispute (Violates Article 27 statutory list)',
      'Continuous 14-day shift without 24-hour weekly rest day (Violates Article 73)'
    ],
    content: `AGREEMENT OF LABOUR EMPLOYMENT

EMPLOYER: Finfinne Agro-Industrial PLC, Dukem Industrial Zone, Oromia / Addis Ababa corridor.
WORKER: Almaz Tadesse, ID: OR-88127.

TERMS OF ENGAGEMENT:

1. DUTIES:
The Worker is employed as Heavy Machinery Plant Operator in the high-heat milling department.

2. OCCUPATIONAL SAFETY AND GEAR:
Due to plant operational costs, the Worker shall be required to supply and purchase their own safety boots, respirator mask, and heavy-duty ear protectors. The Employer shall inspect said equipment upon purchase.

3. SHIFT ROSTER AND WEEKEND HOURS:
To maintain factory continuous production, the Worker shall work consecutive 12-day shifts without intermediate rest days. Work performed on Saturdays and Sundays shall be reimbursed at the standard flat hourly rate without supplementary overtime rate.

4. DISMISSAL CONDITIONS:
The management reserves the right to terminate the Worker immediately without notice or severance pay if the Worker displays disagreement or verbal argument with the shift supervisor.`
  },
  {
    id: 'sample-compliant-bilingual',
    title: 'Commercial Account Executive Agreement (Standard Compliance)',
    organization: 'Abyssinia Logistics & Trading Share Company',
    role: 'Senior Commercial Account Executive',
    type: 'EMPLOYMENT_CONTRACT',
    language: 'ENGLISH',
    description: 'A largely compliant contract grounded accurately in Proclamation No. 1156/2019, providing 60-day probation, 48-hour week, 16 days leave, and 120-day maternity coverage.',
    knownIssues: [
      'Statutory compliance confirmed: 60-day probation strictly observed (Article 9)',
      'Statutory compliance confirmed: 120-day maternity entitlement verified (Article 88)',
      'Recommended observation: Make 3-month notice tier explicit for >9 years tenure (Article 35)'
    ],
    content: `EMPLOYMENT CONTRACT UNDER ETHIOPIAN LABOUR PROCLAMATION NO. 1156/2019

PARTIES:
Employer: Abyssinia Logistics & Trading S.C., Bole Sub-City, Addis Ababa, Ethiopia.
Employee: Bethlehem Girma, Bole Sub-City, Woreda 03, Addis Ababa.

1. POSITION AND NATURE OF WORK:
The Employee is hired as Senior Commercial Account Executive for an indefinite term.

2. PROBATION PERIOD:
The Employee shall complete a probation period of sixty (60) working days in strict compliance with Article 9(2) of Labour Proclamation No. 1156/2019. Upon successful completion, the Employee becomes a permanent employee.

3. NORMAL HOURS OF WORK:
The Employee's normal working hours shall not exceed 8 hours per day and 48 hours per week, in accordance with Article 61 of Proclamation No. 1156/2019. Any required overtime shall be compensated at the statutory rates provided under Article 66.

4. ANNUAL LEAVE:
The Employee is entitled to sixteen (16) working days of annual leave with full pay for the first year of service, incremented by one (1) working day for every additional two years of service as stipulated in Article 76.

5. MATERNITY & FAMILY LEAVE:
Female employees shall be entitled to 120 consecutive days of paid maternity leave (30 days prenatal and 90 days postnatal) pursuant to Article 88. Paternity leave of three (3) consecutive paid days shall be granted pursuant to Article 81.`
  }
];
