import React from "react";
import FeatureCard from "../components/FeatureCard";
import {
	FaCloudUploadAlt,
	FaLock,
	FaFileDownload,
	FaCheckCircle,
	FaBookOpen,
	FaDollarSign,
} from "react-icons/fa";
import { useNavigate } from "react-router-dom";

const LandingPage: React.FC = () => {
	const navigate = useNavigate();

	const goToUploadPage = () => {
		navigate("/upload");
	};

	return (
		<div className="container py-5 text-center">
			<div className="mb-5">
				<img src="/pdf-icon.png" alt="PDF Icon" style={{ width: "100px" }} />
				<h1 className="mt-4 fw-bold">Welcome to TranslatePDF!</h1>
				<p className="text-muted w-75 mx-auto">
					Upload and translate your PDF documents instantly – free, secure, and
					accurate. No sign-up required.
				</p>

				<button className="btn btn-danger mt-3 px-4 py-2" onClick={goToUploadPage}>
					UPLOAD PDF <FaCloudUploadAlt className="ms-2" />
				</button>
			</div>

			<div className="row">
				<FeatureCard
					icon={<FaCloudUploadAlt />}
					title="Upload"
					description="Upload your PDF and translate it quickly."
				/>
				<FeatureCard
					icon={<FaDollarSign />}
					title="Free"
					description="Absolutely free. No sign-up or hidden fees."
				/>
				<FeatureCard
					icon={<FaLock />}
					title="Private"
					description="Files are processed securely and never stored."
				/>
				<FeatureCard
					icon={<FaFileDownload />}
					title="Download"
					description="Get the translated PDF instantly after processing."
				/>
				<FeatureCard
					icon={<FaCheckCircle />}
					title="Accuracy"
					description="Backed by advanced translation AI for high accuracy."
				/>
				<FeatureCard
					icon={<FaBookOpen />}
					title="Readable"
					description="Keep layout and text selectable for readability."
				/>
			</div>
		</div>
	);
};

export default LandingPage;
