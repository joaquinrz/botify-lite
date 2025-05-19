// Token Service Client
// This service handles fetching and caching tokens for API access and Speech Services

const tokenServicePrefix = import.meta.env.VITE_TOKEN_SERVICE_PREFIX;

if (!tokenServicePrefix) {
  console.error('VITE_TOKEN_SERVICE_PREFIX is not defined in the environment variables.');
}

// Cache structure for API token
interface ApiTokenCache {
  token: string;
  expiresAt: number; // Timestamp in milliseconds
}

// Initial empty token cache
let apiTokenCache: ApiTokenCache | null = null;

/**
 * Fetches a new API token from the token service
 * 
 * @returns Promise with the API token
 */
export const getApiToken = async (): Promise<string> => {
  // Check if we have a cached token that's still valid (with 30s buffer)
  const now = Date.now();
  if (apiTokenCache && apiTokenCache.expiresAt > now + 30000) {
    console.log('Using cached API token');
    return apiTokenCache.token;
  }

  try {
    console.log('Fetching new API token');
    const response = await fetch(`${tokenServicePrefix}/api`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch API token: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    
    // Cache the token
    apiTokenCache = {
      token: data.access_token,
      expiresAt: data.expires_on * 1000, // Convert to milliseconds
    };

    return data.access_token;
  } catch (error) {
    console.error('Error fetching API token:', error);
    throw error;
  }
};

/**
 * Clears the API token cache to force a refresh on next request
 */
export const clearApiTokenCache = (): void => {
  apiTokenCache = null;
};
