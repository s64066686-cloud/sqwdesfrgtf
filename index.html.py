
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sheriff Robot View</title>

<style>
    body {
        background: #111827;
        color: white;
        font-family: Arial, sans-serif;
        text-align: center;
    }

    h1 {
        color: #00ff99;
    }

    #screen {
        position: relative;
        width: 90%;
        max-width: 900px;
        margin: auto;
    }

    video, canvas {
        width: 100%;
        border-radius: 10px;
    }

    video {
        display: none;
    }

    canvas {
        background: #222;
        border: 2px solid #00ff99;
    }

    button {
        margin: 15px 5px;
        padding: 12px 24px;
        font-size: 16px;
        cursor: pointer;
        border-radius: 8px;
    }

    #status {
        color: #00ff99;
    }
</style>
</head>

<body>
<h1>🤖 Sheriff Robot View</h1>
<p>웹캠 얼굴 인식 및 좌표 표시 시스템</p>
<p id="status">OpenCV를 불러오는 중...</p>

<div id="screen">
    <video id="video" autoplay playsinline></video>
    <canvas id="canvas"></canvas>
</div>

<button id="start" disabled>카메라 시작</button>
<button id="stop" disabled>카메라 종료</button>

<script async src="https://docs.opencv.org/4.x/opencv.js"></script>

<script>
const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const statusText = document.getElementById("status");
const startBtn = document.getElementById("start");
const stopBtn = document.getElementById("stop");

const CASCADE_URL =
    "https://raw.githubusercontent.com/opencv/opencv/4.x/" +
    "data/haarcascades/haarcascade_frontalface_default.xml";

const WARN_RATIO = 0.35;

let faceCascade = null;
let cameraStream = null;
let running = false;
let busy = false;
let animationId = null;

// OpenCV.js가 준비되면 얼굴 검출기 파일을 불러옴
const cvReady = new Promise((resolve) => {
    const checkOpenCV = () => {
        if (window.cv && cv.Mat) {
            resolve();
        } else {
            setTimeout(checkOpenCV, 100);
        }
    };

    if (window.cv && window.cv.Mat) {
        resolve();
    } else {
        window.cv = window.cv || {};
        window.cv.onRuntimeInitialized = resolve;
        checkOpenCV();
    }
});

async function loadCascade() {
    await cvReady;

    statusText.textContent = "얼굴 검출기를 불러오는 중...";

    const response = await fetch(CASCADE_URL);
    if (!response.ok) {
        throw new Error("얼굴 검출기 다운로드 실패");
    }

    const buffer = await response.arrayBuffer();
    const data = new Uint8Array(buffer);

    const fileName = "face.xml";
    cv.FS_createDataFile("/", fileName, data, true, false, false);

    faceCascade = new cv.CascadeClassifier();

    if (!faceCascade.load(fileName)) {
        throw new Error("얼굴 검출기를 열 수 없습니다.");
    }

    cv.FS_unlink("/" + fileName);

    statusText.textContent = "준비 완료! 카메라 시작을 눌러주세요.";
    startBtn.disabled = false;
}

async function startCamera() {
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: "user",
                width: { ideal: 640 },
                height: { ideal: 480 }
            },
            audio: false
        });

        video.srcObject = cameraStream;
        await video.play();

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        running = true;
        startBtn.disabled = true;
        stopBtn.disabled = false;

        statusText.textContent = "카메라 작동 중";
        drawFrame();
    } catch (error) {
        statusText.textContent =
            "카메라를 사용할 수 없습니다. 권한을 확인하세요.";
        console.error(error);
    }
}

function drawFrame() {
    if (!running || busy) return;

    busy = true;

    try {
        const W = canvas.width;
        const H = canvas.height;

        ctx.save();

        // 거울처럼 좌우 반전
        ctx.translate(W, 0);
        ctx.scale(-1, 1);
        ctx.drawImage(video, 0, 0, W, H);
        ctx.restore();

        const src = cv.imread(canvas);
        const gray = new cv.Mat();
        const faces = new cv.RectVector();

        try {
            cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);

            faceCascade.detectMultiScale(
                gray, faces, 1.2, 5, 0,
                new cv.Size(60, 60),
                new cv.Size()
            );

            for (let i = 0; i < faces.size(); i++) {
                const face = faces.get(i);
                const x = W - face.x - face.width;
                const y = face.y;
                const w = face.width;
                const h = face.height;

                const cx = x + Math.floor(w / 2);
                const cy = y + Math.floor(h / 2);

                const color =
                    w / W > WARN_RATIO ? "#ff3333" : "#00ff66";

                const label =
                    w / W > WARN_RATIO
                    ? "WARNING! TOO CLOSE!"
                    : "TARGET LOCKED";

                // 얼굴 사각형
                ctx.strokeStyle = color;
                ctx.lineWidth = 3;
                ctx.strokeRect(x, y, w, h);

                // 중앙 십자선
                ctx.beginPath();
                ctx.moveTo(cx - 20, cy);
                ctx.lineTo(cx + 20, cy);
                ctx.moveTo(cx, cy - 20);
                ctx.lineTo(cx, cy + 20);
                ctx.stroke();

                // 상태 표시
                ctx.font = "bold 20px Arial";
                ctx.fillStyle = color;

                let ty = y > 30 ? y - 10 : y + h + 25;
                ty = Math.max(22, Math.min(H - 5, ty));

                ctx.fillText(label, x, ty);

                // 얼굴 오른쪽 좌표
                ctx.font = "bold 17px Arial";
                ctx.fillStyle = "#00ffff";

                const coord = `X:${cx} Y:${cy}`;
                const textX = x + w + 10;

                if (textX + 110 < W) {
                    ctx.fillText(coord, textX, cy);
                } else {
                    ctx.fillText(
                        coord,
                        Math.max(0, x - 5),
                        Math.min(H - 5, y + h + 48)
                    );
                }
            }
        } finally {
            src.delete();
            gray.delete();
            faces.delete();
        }
    } catch (error) {
        console.error(error);
    } finally {
        busy = false;
    }

    if (running) {
        animationId = requestAnimationFrame(drawFrame);
    }
}

function stopCamera() {
    running = false;

    if (animationId !== null) {
        cancelAnimationFrame(animationId);
        animationId = null;
    }

    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }

    video.srcObject = null;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    startBtn.disabled = false;
    stopBtn.disabled = true;
    statusText.textContent = "카메라 종료됨";
}

startBtn.addEventListener("click", startCamera);
stopBtn.addEventListener("click", stopCamera);

loadCascade().catch(error => {
    statusText.textContent =
        "초기화 실패: 인터넷 연결을 확인하고 페이지를 새로고침하세요.";
    console.error(error);
});
</script>
</body>
</html>
