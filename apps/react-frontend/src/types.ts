export interface ProductOption {
  sku: string;
  value: number;
}

export interface RecommendedProduct {
  productNumber: string;
  formCode: string;
  title: string;
  description: string;
  options?: ProductOption[];
}

export interface Message {
  role: string;
  content: string;
  timestamp: string;
  recommendedProducts?: RecommendedProduct[];
}
