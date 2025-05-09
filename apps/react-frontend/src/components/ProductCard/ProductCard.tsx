import React from 'react';
import './ProductCard.css';

export interface ProductCardProps {
  title: string;
  description: string;
  productNumber: string;
  formCode: string;
}

const ProductCard: React.FC<ProductCardProps> = ({ title, description, productNumber, formCode }) => {
  const url = `https://www.starbucks.com/menu/product/${productNumber}/${formCode.toLowerCase()}`;
  return (
    <div className="product-card">
      <h3 className="product-card-title">{title}</h3>
      <div className="product-card-desc">{description}</div>
      <button
        className="product-card-btn"
        onClick={() => window.open(url, '_blank', 'noopener,noreferrer')}
      >
        View on Starbucks.com
      </button>
    </div>
  );
};

export default ProductCard;
