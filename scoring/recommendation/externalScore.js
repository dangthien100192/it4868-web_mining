import fetch from "node-fetch";

/**
 * =====================
 * EXTERNAL PROVIDERS
 * =====================
 * Bạn chỉ cần thêm provider mới vào đây
 */
const PROVIDERS = [
    // {
    //     name: "ml_score_v1",
    //     enabled: true,
    //     endpoint: "https://external-api-1/score",
    //     timeoutMs: 800,
    //     weight: 0.5,
    //     fallbackScore: 0.5
    // },
    // {
    //     name: "vendor_score",
    //     enabled: false,
    //     endpoint: "https://external-api-2/score",
    //     timeoutMs: 600,
    //     weight: 0.3,
    //     fallbackScore: 0.6
    // }
];

/**
 * =====================
 * CALL SINGLE PROVIDER
 * =====================
 */
async function callProvider(provider, payload) {
    if (!provider.enabled) {
        return {
            provider: provider.name,
            score: provider.fallbackScore,
            usedFallback: true
        };
    }

    const controller = new AbortController();
    const timer = setTimeout(
        () => controller.abort(),
        provider.timeoutMs
    );

    try {
        const res = await fetch(provider.endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            signal: controller.signal
        });

        if (!res.ok) throw new Error("API error");

        const data = await res.json();
        if (typeof data.score !== "number") {
            throw new Error("Invalid score");
        }

        return {
            provider: provider.name,
            score: data.score,
            usedFallback: false
        };

    } catch (e) {
        console.warn(`⚠️ ${provider.name} fallback`);
        return {
            provider: provider.name,
            score: provider.fallbackScore,
            usedFallback: true
        };
    } finally {
        clearTimeout(timer);
    }
}

/**
 * =====================
 * PUBLIC API
 * =====================
 */
export async function getExternalScore(phone, item) {
    const payload = { phone, item };

    const results = await Promise.all(
        PROVIDERS.map(p => callProvider(p, payload))
    );

    let totalWeight = 0;
    let weightedScore = 0;

    for (const r of results) {
        const provider = PROVIDERS.find(p => p.name === r.provider);
        weightedScore += r.score * provider.weight;
        totalWeight += provider.weight;
    }

    const finalScore =
        totalWeight > 0 ? weightedScore / totalWeight : 0.5;

    return {
        score: +finalScore.toFixed(3),
        detail: results
    };
}
