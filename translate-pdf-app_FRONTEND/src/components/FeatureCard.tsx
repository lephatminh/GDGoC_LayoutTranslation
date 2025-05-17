// src/components/FeatureCard.tsx
import React from 'react';

interface FeatureCardProps {
	icon: React.ReactNode;
	title: string;
	description: string;
}

const FeatureCard: React.FC<FeatureCardProps> = ({ icon, title, description }) => (
	<div className="col-md-4 mb-4">
		<div className="card shadow-sm h-100">
			<div className="card-body text-center">
				<div className="mb-2 fs-3">{icon}</div>
				<h5 className="card-title fw-bold">{title}</h5>
				<p className="card-text">{description}</p>
			</div>
		</div>
	</div>
);

export default FeatureCard;
