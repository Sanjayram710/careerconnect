import os
import json
import requests
from datetime import datetime, timedelta
from models import db, CompanyNewsCache

# Classify news articles based on keywords in title and summary
def classify_article(title, description):
    title_lower = (title or '').lower()
    desc_lower = (description or '').lower()
    text = title_lower + ' ' + desc_lower
    
    tags = []
    if any(k in text for k in ['ai', 'artificial intelligence', 'machine learning', 'gpu', 'llm', 'copilot', 'model', 'nvidia', 'openai', 'claude', 'gemini', 'deepmind', 'tech', 'software', 'cloud', 'quantum']):
        tags.append('AI & Technology')
    if any(k in text for k in ['hiring', 'jobs', 'recruit', 'career', 'layoff', 'team', 'appoint', 'ceo', 'executive', 'talent', 'workforce']):
        tags.append('Hiring & Careers')
    if any(k in text for k in ['launch', 'announce', 'introduce', 'unveil', 'release', 'new product', 'feature', 'unveiled', 'debut']):
        tags.append('Product Launch')
    if any(k in text for k in ['funding', 'acquire', 'acquisition', 'partner', 'partnership', 'deal', 'revenue', 'quarter', 'earnings', 'ipo', 'buyout', 'investment', 'stocks', 'shares', 'valuation']):
        tags.append('Business & Finance')
    
    if not tags:
        tags.append('Announcement')
    return tags

# High-quality mock news database for simulation mode (when no API keys are present)
MOCK_NEWS_DATA = {
    "google": [
        {
            "title": "Google DeepMind Announces Gemini 2.5: Next-Gen Agentic Architecture",
            "source": "TechCrunch",
            "published_at": (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Google DeepMind has officially unveiled Gemini 2.5, which features a breakthrough agentic framework. This updates allows developers to build AI agents capable of planning and executing multi-step operations over long horizons.",
            "url": "https://techcrunch.com/google-gemini-agentic-architecture"
        },
        {
            "title": "Google Cloud Launches New Dedicated AI Region in Bengaluru",
            "source": "The Economic Times",
            "published_at": (datetime.utcnow() - timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "To support surging AI enterprise demand, Google Cloud is launching a new specialized AI infrastructure cluster in India. This region will feature NVIDIA H100 GPU clusters running Google Vertex AI pipelines directly for domestic clients.",
            "url": "https://economictimes.indiatimes.com/google-cloud-bengaluru-ai"
        },
        {
            "title": "Google Recruitment Team Boosts Campus Hiring for Advanced AI Engineers",
            "source": "Wired",
            "published_at": (datetime.utcnow() - timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Google is adjusting its talent acquisition strategy, significantly increasing hiring quotas for new university graduates specializing in machine learning, neural networks, and distributed systems.",
            "url": "https://www.wired.com/google-campus-hiring-ai"
        },
        {
            "title": "Google Partners with Stripe to Streamline Android Payments Ecosystem",
            "source": "Bloomberg",
            "published_at": (datetime.utcnow() - timedelta(days=12)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Google and Stripe announced a major expansion of their decade-long global partnership. Stripe will now power billing and payments inside the Google Workspace Marketplace, enabling immediate developer monetization.",
            "url": "https://www.bloomberg.com/google-stripe-payment-partnership"
        },
        {
            "title": "Google Pixel 10 to Feature Custom TSMC-Manufactured Tensor G5 Processors",
            "source": "The Verge",
            "published_at": (datetime.utcnow() - timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Leaked documents show Google's next flagship smartphone will completely bypass Samsung Foundries. Pixel 10 will adopt TSMC's 3nm nodes, dramatically improving thermal efficiency and on-device machine learning capabilities.",
            "url": "https://www.theverge.com/google-pixel-tensor-g5-tsmc"
        },
        {
            "title": "Google Workspace Rolls Out Global AI Co-Authoring Features",
            "source": "VentureBeat",
            "published_at": (datetime.utcnow() - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Google Docs and Slides are receiving a major layout update with multi-agent collaborative editing tools. Users can now assign dedicated research agents to draft sections concurrently.",
            "url": "https://venturebeat.com/google-workspace-coauthoring-ai"
        }
    ],
    "microsoft": [
        {
            "title": "Microsoft Invests $3.2 Billion in Swedish AI Cloud Infrastructure",
            "source": "Reuters",
            "published_at": (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Microsoft is continuing its massive capital expansion across Europe. This new $3.2 billion initiative aims to double cloud compute capacities in Sweden using specialized low-carbon server setups powered by wind energy.",
            "url": "https://reuters.com/microsoft-sweden-datacenter-expansion"
        },
        {
            "title": "Microsoft Copilot Studio Receives Autonomous Workflow Automations",
            "source": "ZDNet",
            "published_at": (datetime.utcnow() - timedelta(days=6)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "At its annual build conference, Microsoft announced Copilot Studio upgrades allowing business analysts to deploy autonomous software agents. These agents can manage backend database updates and trigger client notifications without manual oversight.",
            "url": "https://www.zdnet.com/microsoft-copilot-studio-agents"
        },
        {
            "title": "Microsoft Azure Surges Ahead in Q3 Cloud Infrastructure Market Share",
            "source": "Bloomberg",
            "published_at": (datetime.utcnow() - timedelta(days=9)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Fueled by extensive OpenAI API usage, Microsoft Azure posted a 29% year-over-year revenue increase in its cloud division, closing the gap against market leader AWS.",
            "url": "https://www.bloomberg.com/microsoft-azure-revenue-q3"
        },
        {
            "title": "Microsoft Announces Global Recruitment Drive for Quantum Computing Scientists",
            "source": "Wired",
            "published_at": (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Microsoft is seeking to hire dozens of quantum research engineers to work in its Redmond and Copenhagen offices. The goal is to build topological qubit hardware architectures for next-decade computing.",
            "url": "https://www.wired.com/microsoft-quantum-recruitment"
        },
        {
            "title": "Microsoft and Adobe Team Up to Integrate Creative Cloud with Microsoft 365",
            "source": "TechCrunch",
            "published_at": (datetime.utcnow() - timedelta(days=18)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Microsoft and Adobe have deepened their enterprise software tie-in. Users can now access Adobe Acrobat and Express features natively inside Teams and Outlook without swapping app screens.",
            "url": "https://techcrunch.com/microsoft-adobe-creative-cloud-integration"
        },
        {
            "title": "Microsoft Announces Surface Pro 11 Powered by Qualcomm Snapdragon X Elite",
            "source": "The Verge",
            "published_at": (datetime.utcnow() - timedelta(days=22)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Microsoft's new ARM-based Surface tablets are beating current Macbook Air configurations in battery life and AI benchmark tests, signaling a major paradigm shift for Windows portable hardware.",
            "url": "https://www.theverge.com/microsoft-surface-pro-11-snapdragon"
        }
    ],
    "nvidia": [
        {
            "title": "NVIDIA Blackwell B200 Superchips Ship to Core Cloud Providers",
            "source": "VentureBeat",
            "published_at": (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "NVIDIA CEO Jensen Huang confirmed the initial shipments of its next-generation Blackwell architecture. Amazon Web Services and CoreWeave are slated to be the first clients to deploy these high-performance compute clusters.",
            "url": "https://venturebeat.com/nvidia-blackwell-superchip-shipping"
        },
        {
            "title": "NVIDIA Market Cap Surpasses $3 Trillion, Eclipsing Global Giants",
            "source": "CNBC",
            "published_at": (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "NVIDIA stock reached an all-time high, pushing its total valuation beyond the $3 trillion milestone. This growth is driven by insatiable global demand for generative AI training chips and hardware acceleration.",
            "url": "https://www.cnbc.com/nvidia-market-cap-3-trillion"
        },
        {
            "title": "NVIDIA Announces CUDA 13 with Native Support for Transformer-Specific Opts",
            "source": "SiliconANGLE",
            "published_at": (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "NVIDIA released its latest GPU compilation suite, CUDA 13. This version introduces compiler-level mathematical simplifications specifically tailored for large language models, promising a 20% runtime acceleration.",
            "url": "https://siliconangle.com/nvidia-cuda-13-transformer"
        },
        {
            "title": "NVIDIA and Tesla Expand Autonomous Robot and FSD Compute Partnership",
            "source": "Bloomberg",
            "published_at": (datetime.utcnow() - timedelta(days=11)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "NVIDIA will supply Tesla with an additional 50,000 H100 and H200 accelerators. This hardware is intended to feed Tesla's Dojo supercomputer training cluster, accelerating Full Self-Driving software development.",
            "url": "https://www.bloomberg.com/nvidia-tesla-fsd-hardware-deal"
        },
        {
            "title": "NVIDIA Launches Accelerated Robotics Lab in Munich, Hiring 500+ Engineers",
            "source": "Reuters",
            "published_at": (datetime.utcnow() - timedelta(days=16)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "NVIDIA is establishing a new research center in Germany focused on the Isaac robotics platform. The company is actively recruiting developers specializing in computer vision, robotics control systems, and edge computing.",
            "url": "https://www.reuters.com/nvidia-munich-robotics-lab"
        },
        {
            "title": "NVIDIA Omniverse Integrates with Apple Vision Pro for Spatial Computing",
            "source": "The Verge",
            "published_at": (datetime.utcnow() - timedelta(days=21)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Industrial designers can now stream complex CAD rendering models from NVIDIA Omniverse directly into Apple Vision Pro headsets with sub-millisecond latencies, facilitating remote industrial design reviews.",
            "url": "https://www.theverge.com/nvidia-omniverse-apple-vision-pro"
        }
    ],
    "stripe": [
        {
            "title": "Stripe Launches Open Banking API and Auto-Billing Suite in the UK",
            "source": "TechCrunch",
            "published_at": (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Stripe has debuted its latest financial integration, allowing merchants to collect direct bank-to-bank payments inside checkout screens. This move completely bypasses interchange fees and cuts transaction costs by up to 80%.",
            "url": "https://techcrunch.com/stripe-open-banking-api-uk"
        },
        {
            "title": "Stripe Valuation Climbs to $70 Billion Following Employee Share Purchase",
            "source": "Bloomberg",
            "published_at": (datetime.utcnow() - timedelta(days=6)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Stripe structured a liquidity agreement enabling current and former employees to sell options to institutional investors, placing Stripe's valuation at a robust $70 billion.",
            "url": "https://www.bloomberg.com/stripe-valuation-70b-liquidity"
        },
        {
            "title": "Stripe Announces Integration with WhatsApp for Small Business Checkout",
            "source": "VentureBeat",
            "published_at": (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Stripe payment pages will now display as native WhatsApp checkout widgets in Brazil and India. This lets consumers securely buy products from neighborhood merchants without leaving chat threads.",
            "url": "https://venturebeat.com/stripe-whatsapp-payment-integration"
        },
        {
            "title": "Stripe Expands Global Engineering Hubs: Actively Hiring Senior Platform Developers",
            "source": "Business Insider",
            "published_at": (datetime.utcnow() - timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Stripe is launching a hiring campaign for its infrastructure engineering teams in Dublin, Seattle, and Singapore. The focus is on scaling API availability and ledger consistency engines.",
            "url": "https://www.businessinsider.com/stripe-engineering-hiring-campaign"
        },
        {
            "title": "Stripe Terminal launches new Tap-to-Pay hardware updates globally",
            "source": "TechCrunch",
            "published_at": (datetime.utcnow() - timedelta(days=19)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Stripe has upgraded its point-of-sale software to support seamless Apple and Android Tap-to-Pay connections across 15 European and Asian nations, simplifying physical storefront checkouts.",
            "url": "https://techcrunch.com/stripe-terminal-tap-to-pay"
        }
    ],
    "adobe": [
        {
            "title": "Adobe Launches Firefly Image 3: Elevating AI-Generated Commercial Assets",
            "source": "Wired",
            "published_at": (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Adobe released its Firefly Image 3 model, bringing photorealistic rendering and text control directly into Photoshop. Adobe guarantees that all training data was sourced from public domains or licensed catalogs.",
            "url": "https://www.wired.com/adobe-firefly-image-3-photoshop"
        },
        {
            "title": "Adobe PDF Reader Integrates AI Conversational Assistant for Document Summaries",
            "source": "ZDNet",
            "published_at": (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Adobe Reader and Acrobat have launched an integrated AI engine. Users can now open 100-page manuals and instantly request summaries, translations, and citations via a chat sidebar.",
            "url": "https://www.zdnet.com/adobe-acrobat-ai-assistant"
        },
        {
            "title": "Adobe Acquires Video Generation Startup to Accelerate Premier Pro AI Features",
            "source": "Bloomberg",
            "published_at": (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "In an effort to rival OpenAI's Sora, Adobe has finalized the acquisition of a video modeling startup. They intend to integrate text-to-video capabilities directly into Premiere Pro by Q3.",
            "url": "https://www.bloomberg.com/adobe-acquires-video-ai-startup"
        },
        {
            "title": "Adobe Announces Global Design Internships and Graduate Hiring Openings",
            "source": "DesignWeek",
            "published_at": (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Adobe is opening applications for its design, software architecture, and product management internship programs. This campaign targets students from international universities for summer placements.",
            "url": "https://www.designweek.co.uk/adobe-student-internships"
        },
        {
            "title": "Adobe Photoshop Updates Introduce Advanced GenFill and Layout Controls",
            "source": "The Verge",
            "published_at": (datetime.utcnow() - timedelta(days=18)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Photoshop has deployed a web client update enabling iPad and Chromebook editors to run Generative Fill tasks in web browsers, drastically cutting memory requirements.",
            "url": "https://www.theverge.com/adobe-photoshop-generative-fill-web"
        }
    ],
    "tesla": [
        {
            "title": "Tesla Showcases FSD V12 Supervised Self-Driving Fleet Growth in the US",
            "source": "The Verge",
            "published_at": (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Tesla has rolled out FSD V12 to all North American subscribers. The update replaces hardcoded C++ code with neural network nodes trained on millions of real-world video frames, showing smoother lane changes.",
            "url": "https://www.theverge.com/tesla-fsd-v12-neural-network"
        },
        {
            "title": "Tesla Model Y Becomes the Best-Selling Passenger Car Globally",
            "source": "Reuters",
            "published_at": (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "According to automotive industry analyst reports, Tesla Model Y has official surpassed traditional combustion engines to become the absolute top-selling vehicle globally across all segments.",
            "url": "https://www.reuters.com/tesla-modely-bestselling-car"
        },
        {
            "title": "Tesla Announces Plans for Next-Generation Gigafactory in Monterrey, Mexico",
            "source": "Bloomberg",
            "published_at": (datetime.utcnow() - timedelta(days=9)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Tesla CEO Elon Musk confirmed land permits are finalized for its upcoming Gigafactory Mexico. The site is expected to specialize in producing Tesla's upcoming next-generation $25,000 EV platform.",
            "url": "https://www.bloomberg.com/tesla-mexico-gigafactory-approved"
        },
        {
            "title": "Tesla Hiring Core Robotics Developers to Scale Optimus Humanoid Program",
            "source": "Electrek",
            "published_at": (datetime.utcnow() - timedelta(days=13)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Tesla has posted multiple job listings seeking actuators designers, safety controls engineers, and computer vision specialists to work on the Optimus humanoid robot project in Palo Alto.",
            "url": "https://electrek.co/tesla-optimus-robotics-hiring"
        },
        {
            "title": "Tesla and Panasonic Sign Agreement to Boost US Battery Cell Production",
            "source": "Nikkei Asia",
            "published_at": (datetime.utcnow() - timedelta(days=17)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": "Panasonic will supply Tesla with next-gen 4680 cylindrical batteries, expanding US local production capacity by 20% to qualify for government clean energy subsidies.",
            "url": "https://asia.nikkei.com/tesla-panasonic-battery-deal"
        }
    ]
}

# General fallback mock news if the company name doesn't match predefined companies
def get_generic_mock_news(company_name):
    return [
        {
            "title": f"{company_name} Announces Breakthrough Expansion and Digital Transformation",
            "source": "MarketWatch",
            "published_at": (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": f"{company_name} has announced a major strategic expansion aimed at strengthening its market presence. The initiative is projected to create new avenues of growth and technical improvements.",
            "url": "#"
        },
        {
            "title": f"{company_name} Launching Nationwide Recruitment and Internship Campaigns",
            "source": "Business Insider",
            "published_at": (datetime.utcnow() - timedelta(days=6)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": f"In a press briefing, {company_name} revealed plans for a global talent acquisition campaign, aiming to hire hundreds of engineers and support managers across various operations.",
            "url": "#"
        },
        {
            "title": f"{company_name} Debuts New AI-Powered Enterprise Analytics Service",
            "source": "VentureBeat",
            "published_at": (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": f"{company_name} is rolling out its latest software suite which integrates machine learning modules. This service will help clients process complex database operations with automated assistance.",
            "url": "#"
        },
        {
            "title": f"{company_name} Partners with Global Tech Consortium for Sustainability Initiatives",
            "source": "TechCrunch",
            "published_at": (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": f"{company_name} has joined hands with top industry entities to reduce carbon outputs across its hardware supply chains, aiming for zero net emissions by the end of the decade.",
            "url": "#"
        },
        {
            "title": f"{company_name} Posts Solid Q1 Revenue Growth and Exceeds Analysts Expectations",
            "source": "Bloomberg",
            "published_at": (datetime.utcnow() - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": f"{company_name} announced its quarterly financial statements, showing a healthy 14% year-over-year revenue gain. This success was credited to stable performance in key regional sales.",
            "url": "#"
        }
    ]

# Fetch news from API (GNews or NewsAPI) or return simulation fallback
def fetch_company_news_from_api(company_name):
    gnews_key = os.getenv("GNEWS_API_KEY")
    newsapi_key = os.getenv("NEWS_API_KEY")
    
    articles = []
    
    # Mode 1: GNews
    if gnews_key and gnews_key.strip():
        try:
            url = f"https://gnews.io/api/v4/search?q={company_name}&lang=en&max=10&apikey={gnews_key}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "articles" in data:
                    for art in data["articles"]:
                        articles.append({
                            "title": art.get("title"),
                            "source": art.get("source", {}).get("name", "GNews Partner"),
                            "published_at": art.get("publishedAt"),
                            "summary": art.get("description") or art.get("content"),
                            "url": art.get("url")
                        })
                    print(f"GNews successfully fetched {len(articles)} articles for {company_name}")
                    return articles
            print(f"GNews returned status {response.status_code} for query '{company_name}'")
        except Exception as e:
            print(f"GNews API request failed: {str(e)}")
            
    # Mode 2: NewsAPI
    elif newsapi_key and newsapi_key.strip():
        try:
            url = f"https://newsapi.org/v2/everything?q={company_name}&language=en&sortBy=publishedAt&pageSize=10&apiKey={newsapi_key}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "articles" in data:
                    for art in data["articles"]:
                        articles.append({
                            "title": art.get("title"),
                            "source": art.get("source", {}).get("name", "NewsAPI"),
                            "published_at": art.get("publishedAt"),
                            "summary": art.get("description") or art.get("content"),
                            "url": art.get("url")
                        })
                    print(f"NewsAPI successfully fetched {len(articles)} articles for {company_name}")
                    return articles
            print(f"NewsAPI returned status {response.status_code} for query '{company_name}'")
        except Exception as e:
            print(f"NewsAPI request failed: {str(e)}")
            
    # Mode 3: Simulation Fallback
    comp_key = company_name.lower().strip()
    if comp_key in MOCK_NEWS_DATA:
        print(f"Simulation Mode: Using predefined mock dataset for {company_name}")
        return MOCK_NEWS_DATA[comp_key]
    else:
        print(f"Simulation Mode: Using generic fallback mock dataset for {company_name}")
        return get_generic_mock_news(company_name)

# Get company news with caching (1-hour TTL)
def get_company_news(company_name, force_refresh=False):
    now = datetime.utcnow()
    cache_record = CompanyNewsCache.query.filter_by(company_name=company_name).first()
    
    # Check cache validity
    if cache_record and not force_refresh:
        # 1 hour TTL
        if now - cache_record.updated_at < timedelta(hours=1):
            try:
                articles = json.loads(cache_record.news_json)
                # Assign dynamic tags
                for art in articles:
                    art["tags"] = classify_article(art.get("title"), art.get("summary"))
                return articles, False  # Return articles, was_cached = True (wait, return False for "is_refreshed")
            except Exception as e:
                print(f"Cache read error for {company_name}, rebuilding cache: {str(e)}")
                
    # Cache miss or expired or forced refresh
    try:
        articles = fetch_company_news_from_api(company_name)
        # Limit to 10 articles
        articles = articles[:10]
        
        # Save to DB cache
        if cache_record:
            cache_record.news_json = json.dumps(articles)
            cache_record.updated_at = now
        else:
            new_cache = CompanyNewsCache(
                company_name=company_name,
                news_json=json.dumps(articles)
            )
            db.session.add(new_cache)
            
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Failed to cache news for {company_name}: {str(e)}")
        # If caching failed, still return the fetched/simulated articles
        if not articles:
            articles = get_generic_mock_news(company_name)
            
    # Assign dynamic tags
    for art in articles:
        art["tags"] = classify_article(art.get("title"), art.get("summary"))
        
    return articles, True
