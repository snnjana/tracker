/** API client for communicating with the backend. */

import type { ErrorResponse, IncidentReport, InvestigationInput } from '../types';

const API_BASE_URL = '/api';

export class ApiError extends Error {
  public code: string;
  public details?: string;

  constructor(response: ErrorResponse) {
    super(response.message);
    this.code = response.code;
    this.details = response.details;
    this.name = 'ApiError';
  }
}

export async function investigate(input: InvestigationInput): Promise<IncidentReport> {
  const response = await fetch(`${API_BASE_URL}/investigate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    let errorData: ErrorResponse;
    try {
      const body = await response.json();
      // FastAPI wraps errors in a "detail" field
      errorData = body.detail || body;
    } catch {
      errorData = {
        code: 'UNKNOWN_ERROR',
        message: `Request failed with status ${response.status}`,
      };
    }
    throw new ApiError(errorData);
  }

  return response.json();
}
