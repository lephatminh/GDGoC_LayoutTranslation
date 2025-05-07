import React, { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { Worker, Viewer } from "@react-pdf-viewer/core";
import "@react-pdf-viewer/core/lib/styles/index.css";

const ViewPage: React.FC = () => {
	const location = useLocation();
	const { originalUrl, translatedUrl } = location.state;

	const leftRef = useRef<HTMLDivElement>(null);
	const rightRef = useRef<HTMLDivElement>(null);
	const isSyncingScroll = useRef(false); // Prevent recursive sync

	useEffect(() => {
		const syncScroll = (source: HTMLDivElement, target: HTMLDivElement) => {
			if (isSyncingScroll.current) return;
			isSyncingScroll.current = true;

			const ratio = source.scrollTop / (source.scrollHeight - source.clientHeight);
			target.scrollTop = ratio * (target.scrollHeight - target.clientHeight);

			setTimeout(() => (isSyncingScroll.current = false), 20);
		};

		const left = leftRef.current;
		const right = rightRef.current;

		if (left && right) {
			left.addEventListener("scroll", () => syncScroll(left, right));
			right.addEventListener("scroll", () => syncScroll(right, left));
		}

		return () => {
			if (left && right) {
				left.removeEventListener("scroll", () => syncScroll(left, right));
				right.removeEventListener("scroll", () => syncScroll(right, left));
			}
		};
	}, []);

	return (
		<div className="d-flex" style={{ height: "100vh" }}>
			<Worker workerUrl="https://unpkg.com/pdfjs-dist@3.4.120/build/pdf.worker.min.js">
				<div
					ref={leftRef}
					style={{ flex: 1, overflowY: "scroll", borderRight: "1px solid #ccc" }}
				>
					<Viewer fileUrl={originalUrl} />
				</div>
				<div
					ref={rightRef}
					style={{ flex: 1, overflowY: "scroll" }}
				>
					<Viewer fileUrl={translatedUrl} />
				</div>
			</Worker>
		</div>
	);
};

export default ViewPage;
