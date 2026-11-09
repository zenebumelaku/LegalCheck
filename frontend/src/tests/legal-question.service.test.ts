import { ApiError } from '../lib/api-client';
import {
  LegalQuestionService,
  LegalQuestionConversationResult
} from '../services/legal-question.service';

function assert(condition: boolean, message: string): void {
  if (!condition) throw new Error(`TEST FAILED: ${message}`);
  console.log(`✓ PASS: ${message}`);
}

async function withMockedFetch(
  response: Response,
  run: (requests: Array<{ url: string; init?: RequestInit }>) => Promise<void>
): Promise<void> {
  const originalFetch = globalThis.fetch;
  const requests: Array<{ url: string; init?: RequestInit }> = [];
  globalThis.fetch = async (input, init) => {
    requests.push({ url: String(input), init });
    return response;
  };
  try {
    await run(requests);
  } finally {
    globalThis.fetch = originalFetch;
  }
}

async function runTests(): Promise<void> {
  console.log('\n--- Running Legal Q&A API Client Tests ---');

  const result: LegalQuestionConversationResult = {
    conversation_id: 'test-conversation-id',
    answer: {
      status: 'answered',
      question: 'A synthetic test question?',
      answer: 'A synthetic test response.',
      review_date: '2025-01-01',
      citations: [],
      model_name: 'mock-provider',
      model_version: 'test',
      cache_hit: true,
      disclaimer: 'Test fixture only.'
    }
  };

  await withMockedFetch(
    new Response(JSON.stringify(result), { status: 201 }),
    async requests => {
      const response = await LegalQuestionService.askInConversation({
        question: ' A synthetic test question? ',
        conversation_id: 'conversation-id',
        review_context: { jurisdiction: 'ET', include_unverified: false }
      });
      const request = requests[0];
      assert(
        request.url.endsWith('/api/v1/legal-questions/conversations'),
        'Question submission calls the conversation API'
      );
      assert(request.init?.method === 'POST', 'Question submission uses POST');
      assert(
        JSON.parse(String(request.init?.body)).question ===
          ' A synthetic test question? ',
        'Question submission sends the entered prompt without fabricating a response'
      );
      assert(response.answer.cache_hit, 'The backend cache status is preserved');
    }
  );

  await withMockedFetch(
    new Response(JSON.stringify({ items: [], limit: 20, offset: 40, total: 0 }), {
      status: 200
    }),
    async requests => {
      const page = await LegalQuestionService.listConversations(20, 40);
      assert(
        requests[0].url.endsWith('?limit=20&offset=40'),
        'Conversation history forwards pagination parameters'
      );
      assert(page.offset === 40, 'Conversation history returns the API page');
    }
  );

  await withMockedFetch(
    new Response(JSON.stringify({ id: 'conversation/one', messages: [] }), {
      status: 200
    }),
    async requests => {
      await LegalQuestionService.getConversation('conversation/one');
      assert(
        requests[0].url.endsWith('/conversation%2Fone'),
        'Conversation identifiers are URL encoded'
      );
    }
  );

  await withMockedFetch(new Response(null, { status: 204 }), async requests => {
    await LegalQuestionService.deleteConversation('conversation-id');
    assert(
      requests[0].init?.method === 'DELETE',
      'Conversation deletion uses the backend delete endpoint'
    );
  });

  await withMockedFetch(
    new Response(JSON.stringify({ detail: 'AI generation is unavailable.' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    }),
    async () => {
      let failedWithApiError = false;
      try {
        await LegalQuestionService.askInConversation({
          question: 'A synthetic test question?'
        });
      } catch (error) {
        failedWithApiError =
          error instanceof ApiError &&
          error.status === 503 &&
          error.message === 'AI generation is unavailable.';
      }
      assert(
        failedWithApiError,
        'Provider errors surface from the API instead of falling back to a sample answer'
      );
    }
  );

  console.log('--- All Legal Q&A API Client Tests Passed ---\n');
}

void runTests();
