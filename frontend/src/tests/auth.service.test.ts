import { ApiError } from '../lib/api-client';
import { AuthService } from '../services/auth.service';

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
  console.log('\n--- Running Password Reset API Client Tests ---');

  await withMockedFetch(
    new Response(JSON.stringify({ message: 'If an account exists, email may be sent.' }), {
      status: 202
    }),
    async requests => {
      const result = await AuthService.requestPasswordReset('person@example.com');
      assert(result.success, 'A successful reset request reflects the backend response');
      assert(
        requests[0].url.endsWith('/api/v1/auth/password-reset-request'),
        'Reset request calls the backend password-reset endpoint'
      );
      assert(
        JSON.parse(String(requests[0].init?.body)).email === 'person@example.com',
        'Reset request sends the entered email'
      );
    }
  );

  await withMockedFetch(
    new Response(JSON.stringify({ message: 'Password has been reset.' }), {
      status: 200
    }),
    async requests => {
      const result = await AuthService.confirmPasswordReset(
        'opaque-one-time-token',
        'a-new-password-value'
      );
      assert(
        requests[0].url.endsWith('/api/v1/auth/password-reset-confirm'),
        'Confirmation calls the backend token-consumption endpoint'
      );
      assert(
        JSON.parse(String(requests[0].init?.body)).token === 'opaque-one-time-token',
        'Confirmation sends the one-time token to the backend'
      );
      assert(result.message === 'Password has been reset.', 'Confirmation returns backend text');
    }
  );

  await withMockedFetch(
    new Response(JSON.stringify({ error: { message: 'Password reset email is not configured.' } }), {
      status: 503
    }),
    async () => {
      try {
        await AuthService.requestPasswordReset('person@example.com');
        throw new Error('Expected the unavailable-provider error.');
      } catch (error) {
        assert(
          error instanceof ApiError &&
            error.message === 'Password reset email is not configured.',
          'Provider configuration errors are surfaced instead of shown as success'
        );
      }
    }
  );
}

runTests().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
