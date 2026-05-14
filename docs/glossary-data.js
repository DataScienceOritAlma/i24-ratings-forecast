// ============================================
// Glossary data — 50+ terms across 13 categories
// Source: GLOSSARY.md
// ============================================

const CATEGORIES = {
  tv:       { name: 'טלוויזיה',         emoji: '📺' },
  metrics:  { name: 'מטריקות',           emoji: '📊' },
  split:    { name: 'פיצול נתונים',      emoji: '✂️' },
  feature:  { name: 'הנדסת פיצ\'רים',    emoji: '🔧' },
  problem:  { name: 'בעיות בדאטה',       emoji: '⚠️' },
  linear:   { name: 'מודלים ליניאריים',  emoji: '📈' },
  reg:      { name: 'רגולריזציה',         emoji: '🎯' },
  trees:    { name: 'עצים',               emoji: '🌳' },
  boost:    { name: 'Boosting',          emoji: '🚀' },
  other:    { name: 'מודלים נוספים',     emoji: '🧩' },
  ensemble: { name: 'Ensembles',         emoji: '🎭' },
  calib:    { name: 'כיול',               emoji: '🎚️' },
  infra:    { name: 'תשתית',              emoji: '⚙️' },
};

const TERMS = [
  // ===== TV =====
  {
    cat: 'tv', emoji: '📡', name: 'רייטינג (Rating)',
    kid: 'דמיין שבמדינה יש 100 ילדים. אם 7 מהם צפו בתוכנית "המוסיקלי", הרייטינג שלה הוא 7. הרייטינג זה אחוז מכלל הצופים הפוטנציאלים שצפו.',
    tech: 'אחוז משקי הבית שצפו בתוכנית מתוך אוכלוסיית היעד (פאנל מדידה). נמדד על ידי מד-טלוויזיה (PeopleMeter) במדגם של 800-1000 בתי-אב מייצגים. נוסחה: <code>(מספר בתי-אב שצפו ≥ 1 דקה) / (סך בתי-אב בפאנל) × 100</code>.',
    where: 'העמודה הראשית בדאטה (<code>ר\' אמיתי</code>). זה הערך שניבאנו — היעד (<code>y</code>) של כל המודלים.'
  },
  {
    cat: 'tv', emoji: '🥧', name: 'נתח (Share)',
    kid: 'דמיין שמ-100 ילדים, רק 20 הדליקו טלוויזיה. אם 14 מהם צפו ב"המוסיקלי", הנתח הוא 70% (14 מתוך 20). הנתח אומר <strong>מתוך אלה שצופים בטלוויזיה עכשיו, כמה צופים בי</strong>.',
    tech: '<code>אחוז צופים בתוכנית / HUT × 100</code>. נתח מנטרל את גודל קהל הצופים הכולל בשעה — מודד תחרותיות יחסית.',
    where: 'עמודה משנית (<code>נתח אמיתי</code>) — לא ניבאנו אותה ב-MVP אבל היא קיימת בדאטה.'
  },
  {
    cat: 'tv', emoji: '📺', name: 'HUT (Households Using TV)',
    kid: 'מה אחוז הילדים שכרגע מדליקים טלוויזיה בכלל (לא משנה איזה ערוץ). בלילה זה הרבה, בבוקר זה מעט.',
    tech: 'אחוז משקי הבית שמכשיר הטלוויזיה דולק אצלם ברגע נתון. תלוי בשעה, יום, עונה, אירועים. מסביר חלק גדול מהשונות ברייטינג בין רצועות.',
    where: 'מהונדס כפיצ\'ר — <code>HUT_estimated</code> — לפי שעה ויום שבוע. עזר למודל להבין שב-23:00 הרייטינג אמור להיות נמוך גם אם תוכנית טובה.'
  },
  {
    cat: 'tv', emoji: '🕐', name: 'רצועה (Slot)',
    kid: 'היום בטלוויזיה מחולק לקופסאות זמן. כל קופסה זה רצועה. למשל "ראשון 20:00–21:00" זה רצועה. גם "שבת 14:00–16:00" זה רצועה.',
    tech: 'חלון זמן קבוע + יום שבוע. בפרוייקט הגדרנו <code>slot_key = day_of_week + hour</code>. שימושי כי תוכניות באותה רצועה לרוב מקבלות רייטינג דומה (אותו קהל).',
    where: 'פיצ\'ר <code>slot_avg_rating</code> — ממוצע רייטינג היסטורי באותה רצועה. שימש כ-baseline חכם וגם כפיצ\'ר במודלים מתקדמים.'
  },
  {
    cat: 'tv', emoji: '🫁', name: 'פאנל נושם',
    kid: 'כדי לדעת מה כל המדינה רואה, אי אפשר לבדוק אצל כולם. אז בוחרים קבוצה קטנה שמייצגת את כולם, ובכל כמה חודשים מחליפים חלק מהקבוצה — שלא ייתקעו עם אותם אנשים לנצח.',
    tech: 'מדגם פעיל של בתי-אב (800-1000) המייצג את אוכלוסיית הצופים. "נושם" = רוטציה — כ-15-20% מהמדגם מתחלף מדי שנה. שומר על ייצוגיות ומונע bias של היכרות.',
    where: 'רקע כללי להבנת הדאטה. רוטציה היא מקור לרעש (noise) — שני בתי-אב שונים יתנו רייטינג שונה לאותה תוכנית.'
  },
  {
    cat: 'tv', emoji: '🌟', name: 'פריים טיים',
    kid: 'השעות בערב שהכי הרבה אנשים צופים בטלוויזיה. בישראל זה ב-20:00 עד 23:00.',
    tech: 'מקטע השעות עם ה-HUT הגבוה ביותר ביום. תלוי בערוץ ובקהל היעד. ב-i24 הפעילות החיה השיאית היא 17:00–22:00 (חדשות + דיונים).',
    where: 'ב-V1 הגדרנו ידנית 18:00–21:00 (תוקן בעקבות הערה מהמשתמשת). בגרסה הנוכחית של דף החיזוי העתידי, המשתמשת מזינה שעת התחלה וסיום מדויקות, אז לא צריך לקטלג ידנית.'
  },

  // ===== Metrics =====
  {
    cat: 'metrics', emoji: '📏', name: 'MAE (Mean Absolute Error)',
    kid: 'דמייני שניחשת לאמא מה גובה הילד שלה ב-7 מקרים. בכל פעם טעית בכמה ס"מ. אם תיקח את כל הטעויות, תהפוך אותן לחיוביות (גם +3 וגם -3 הופכות ל-3), ותעשה ממוצע — זה ה-MAE. כמה ס"מ בממוצע אתה טועה.',
    tech: '<code>MAE = (1/n) × Σ |y_real - y_pred|</code>. מדד שגיאה ממוצעת באותן יחידות של היעד. עמיד יחסית לחריגים (outliers) בהשוואה ל-MSE. תמיד ≥ 0; ככל שקטן, טוב יותר.',
    where: 'המדד הראשי שלנו. <strong>MAE=0.263</strong> של HistGradientBoosting פירושו: בממוצע אנחנו טועים ב-0.263 נקודות רייטינג. זה ~6.5 אלף בתי-אב.'
  },
  {
    cat: 'metrics', emoji: '📐', name: 'RMSE (Root Mean Squared Error)',
    kid: 'כמו MAE, אבל עם "עונש" כפול לטעויות גדולות. אם טעית פעם אחת ב-10 ס"מ ופעם אחת ב-1 ס"מ, ה-MAE שלך הוא 5.5 וה-RMSE שלך הוא 7.1. ה-RMSE קופץ יותר כשיש "פיצוצים".',
    tech: '<code>RMSE = √[(1/n) × Σ (y_real - y_pred)²]</code>. ריבוע מעצים שגיאות גדולות. תמיד ≥ MAE. שימושי כשטעויות חריגות גרועות במיוחד.',
    where: 'מדד משני. כשה-RMSE רחוק מה-MAE → סימן לחריגים גדולים (למשל שאגת הארי שטעינו בה 1.5 נקודות).'
  },
  {
    cat: 'metrics', emoji: '🎯', name: 'R² (R-squared)',
    kid: 'אם תמיד תנחש את אותו ערך (הממוצע) — תקבל ציון 0. אם תנחש מושלם כל פעם — תקבל 1. אם תנחש גרוע יותר מהממוצע — תקבל מספר שלילי. R² אומר "כמה אחוז מהבלגן בדאטה אני מסביר".',
    tech: '<code>R² = 1 - (SS_res / SS_tot)</code>, כאשר <code>SS_res = Σ(y - ŷ)²</code> ו-<code>SS_tot = Σ(y - ȳ)²</code>. ערכים: ≤1. 1 = מושלם, 0 = כמו לנחש ממוצע, שלילי = גרוע מממוצע.',
    where: '<strong>R²=0.603</strong> של HistGradientBoosting → המודל מסביר 60.3% מהשונות ברייטינג. שאר 39.7% זה רעש + אירועים בלתי-צפויים (drift).'
  },

  // ===== Split =====
  {
    cat: 'split', emoji: '✂️', name: 'Train/Test Split',
    kid: 'דמיין שאת לומדת למבחן. תקראי 80% מהדפים בספר ותנסי לפתור את ה-20% האחרונים בעצמך — בלי להציץ. אם הצלחת בלי להציץ, סימן שבאמת למדת. ככה בודקים מודל.',
    tech: 'מחלקים את הדאטה לסט אימון (80%, המודל "רואה" אותו) וסט בחינה (20%, נסתר מהמודל). מאמנים על האימון, בודקים על הבחינה. מודד יכולת הכללה (generalization).',
    where: 'כל המודלים. החיתוך: <strong>2026-02-08</strong> (כל מה שלפני = train, אחרי = test).'
  },
  {
    cat: 'split', emoji: '📅', name: 'פיצול כרונולוגי',
    kid: 'את לא יכולה לבחור מבחן ולומר "אני אלמד מהשאלות 1, 3, 5 ואבחן את עצמי על 2, 4, 6" — אם השאלות תלויות בסדר, את מרמה את עצמך. בדאטה של זמן, את חייבת ללמוד מהעבר ולחזות את העתיד. לא לסמן אקראי.',
    tech: 'במקום פיצול רנדומלי, חותכים לפי תאריך — train = עבר, test = עתיד. מונע leakage של מידע עתידי אל האימון. קריטי לסדרות עיתיות.',
    where: '<strong>חיתוך 2026-02-08</strong>: ~80% אימון, 20% בחינה. אם היינו עושים פיצול רנדומלי, המודל היה "מרגל" — לומד מתוכנית של אפריל ומנבא על תוכנית של ינואר.'
  },
  {
    cat: 'split', emoji: '🔄', name: 'Cross-Validation',
    kid: 'במקום מבחן אחד, את עושה כמה מבחנים קטנים על חתיכות שונות של החומר, כדי להיות בטוחה שהציון שלך הוא לא במזל.',
    tech: 'Cross-validation = הרצה חוזרת של מודל על k חתיכות שונות, ממצעים ביצועים. TimeSeriesSplit הוא K-fold מותאם לזמן — כל fold משתמש בעבר לאימון ובעתיד מיד אחריו לבחינה (extending window).',
    where: 'בכיוון פרמטרים של RandomForest (<code>GridSearchCV</code> עם TimeSeriesSplit), כדי שכל hyperparameter combination ייבחן בכמה חתכים.'
  },

  // ===== Feature Engineering =====
  {
    cat: 'feature', emoji: '🔧', name: 'Feature Engineering',
    kid: 'דמייני שמראים לך תאריך לידה ושואלים מי מבוגר. במקום להגיד למחשב "10/05/2010" — את הופכת את זה ל-"גיל = 15 שנים". הופכים מספר גולמי למשמעות שהמחשב יכול להבין.',
    tech: 'יצירת משתנים חדשים מהדאטה הגולמי כדי לעזור למודל ללמוד דפוסים. זה הצעד החשוב ביותר ב-ML מסורתי — לרוב גורם להבדל גדול יותר בביצועים מבחירת המודל.',
    where: 'הוספנו <strong>19 פיצ\'רים מהונדסים</strong>: lag features, slot averages, HUT estimate, day part, is_weekend, days_since_premiere, event flags ועוד.'
  },
  {
    cat: 'feature', emoji: '⏪', name: 'Lag Features',
    kid: 'איך תנחשי כמה גלידה תקני מחר? כנראה לפי כמה גלידה קנית בשבוע שעבר. ה-"שבוע שעבר" זה ה-lag.',
    tech: 'ערכי היעד מתקופות קודמות כפיצ\'רים. דוגמאות: <code>lag_1</code> = הרייטינג של אותה תוכנית בשידור הקודם, <code>lag_4</code> = ממוצע 4 שידורים אחרונים. דורש זהירות — להשתמש <em>רק</em> בערכים שקדמו לשורה הנוכחית.',
    where: '<code>program_lag_1</code>, <code>program_lag_mean3</code>, <code>slot_lag_mean5</code>. ב-<code>utils/predict.py</code> חישבנו אותם בזמן אמת מ-90 הימים האחרונים, לכל חיזוי עתידי.'
  },
  {
    cat: 'feature', emoji: '🟢', name: 'One-Hot Encoding',
    kid: 'איך אומרים למחשב "יום שלישי"? לא כותבים "שלישי" — כי מחשב לא מבין מילים. במקום זה מציירים שורה עם 7 משבצות (אחת לכל יום) ושמים 1 רק במשבצת של שלישי, 0 בכל השאר. זה One-Hot.',
    tech: 'המרת משתנה קטגוריאלי לכמה משתנים בינאריים. ל-K קטגוריות → K עמודות, רק אחת = 1. מונע מהמודל לחשוב שיש סדר נומרי בקטגוריות.',
    where: 'ב-<code>Pipeline</code> של scikit-learn, <code>OneHotEncoder(handle_unknown=\'ignore\')</code> על עמודות כמו <code>יום בשבוע</code>, <code>סוג תוכנית</code>, <code>שם תוכנית</code>.'
  },
  {
    cat: 'feature', emoji: '⚖️', name: 'Standardization (Z-Score)',
    kid: 'דמייני שיש לך טבלה עם גובה (מטרים: 1-2) ומשקל (קילו: 30-100). המחשב יחשוב שהמשקל הרבה יותר חשוב כי המספרים גדולים. כדי שזה יהיה הוגן, מורידים ממוצע ומחלקים בסטיית תקן. עכשיו כולם בערך 0-1.',
    tech: '<code>z = (x - μ) / σ</code>. הופך כל פיצ\'ר לממוצע 0, סטיית תקן 1. קריטי למודלים מבוססי-מרחק (KNN, SVR) או מבוססי-גרדיאנט (Linear, MLP).',
    where: '<code>StandardScaler</code> במודלים ליניאריים (Ridge, Lasso) וב-MLP. בעצים (RF, XGB) לא צריך — עצים לא מושפעים מסקלה.'
  },
  {
    cat: 'feature', emoji: '🕳️', name: 'Imputation (השלמת חסרים)',
    kid: 'דמייני שבטבלה יש משבצת ריקה. מה שמים שם? אפשר להחליט "תמיד נשים את הממוצע" או "תמיד נשים 0". זה Imputation.',
    tech: 'מילוי ערכים חסרים (<code>NaN</code>). אסטרטגיות: median, mean, constant, most_frequent, KNNImputer (לפי שכנים). חשוב להחליט באימון בלבד ולהשתמש באותם ערכים בבחינה (אחרת — leakage).',
    where: '<code>utils/imputers.py</code> — <code>SimpleMedianImputer</code> (לעמודות מספריות), <code>SimpleConstantImputer(\'unknown\')</code> (לקטגוריאליות). בלי זה — שורות עם חסרים היו נופלות.'
  },

  // ===== Data Problems =====
  {
    cat: 'problem', emoji: '💧', name: 'Data Leakage (דליפת מידע)',
    kid: 'דמייני שאת נבחנת על שאלות, אבל בטעות התשובה כתובה בקטן בפינת הדף. את "תצליחי" — אבל לא באמת למדת. זה Leakage.',
    tech: 'כשמידע מהעתיד או מהיעד "דולף" לפיצ\'רים של האימון. גורם לציון מבחן מנופח שלא משוחזר במציאות. גורמים נפוצים: עמודות שנמדדו אחרי האירוע, normalization על כל הדאטה לפני פיצול, target encoding בלי CV.',
    where: '<strong>הוצאנו מה-features עמודות שנמדדו אחרי השידור</strong> (כמו <code>נתח אמיתי</code> — נמדד יחד עם הרייטינג). Lag features חושבו רק מהיסטוריה שלפני כל שורה.'
  },
  {
    cat: 'problem', emoji: '🌊', name: 'Drift (סחיפת התפלגות)',
    kid: 'למדת לזהות כלבים מצילומים של חצי-שנה. פתאום מראים לך תמונות חדשות עם זן כלב שלא ראית — נכשלת. העולם השתנה והדאטה השתנה.',
    tech: 'שינוי בהתפלגות הדאטה לאורך זמן. סוגים: <strong>concept drift</strong> (היחס feature→y משתנה), <strong>covariate drift</strong> (התפלגות ה-X משתנה). פוגע בכל המודלים שלא מתעדכנים.',
    where: '<strong>שאגת הארי</strong> (אוקטובר 2026) הייתה drift קלאסי — אירוע ביטחוני בלתי-צפוי קפץ את הרייטינג ב-2-3 נקודות לכל הערוץ. אף מודל לא ניבא אותו. זו תקרת הביצועים שלנו.'
  },
  {
    cat: 'problem', emoji: '🥶', name: 'Cold-Start',
    kid: 'איך תנחשי כמה אנשים יבואו למסעדה חדשה ביום הראשון שלה? אין לך שום היסטוריה. את חייבת לסמוך על מסעדות דומות באזור.',
    tech: 'אין היסטוריה לישות חדשה (תוכנית חדשה, משתמש חדש). lag features = NaN. פתרונות: fallback לממוצע קטגוריה, similarity-based imputation, content-based features.',
    where: 'לתוכניות חדשות (פחות מ-3 שידורים) חישבנו lag כממוצע הרצועה במקום ממוצע התוכנית. מודל ה-MVP פחות מדויק עליהן.'
  },
  {
    cat: 'problem', emoji: '🪞', name: 'Overfitting (התאמת-יתר)',
    kid: 'למדת בעל-פה את כל השאלות במבחני העבר — אבל לא הבנת את החומר. במבחן שאלה חדשה הופיעה — נכשלת. זה overfitting.',
    tech: 'המודל לומד גם את הרעש בסט האימון, לא רק את האות. סימן: ביצועים מעולים על train, גרועים על test. פתרון: regularization, יותר דאטה, פחות פיצ\'רים, מודל פחות מורכב.',
    where: 'ב-RandomForest המקורי ראינו <code>train R² = 0.95</code> אבל <code>test R² = 0.4</code> — overfitting קלאסי. תוקן עם hyperparameter tuning (max_depth, min_samples_leaf).'
  },
  {
    cat: 'problem', emoji: '😴', name: 'Underfitting',
    kid: 'ניסית ללמוד אנגלית רק על ידי קריאת המילה "hello". כשבמבחן שאלו מילים אחרות — אין סיכוי. המודל פשוט פשטני מדי.',
    tech: 'המודל לא לומד מספיק מהדאטה — חלש מדי או רגולריזציה חזקה מדי. סימן: ביצועים גרועים גם על train וגם על test.',
    where: 'המודל הנאיבי (חיזוי = ממוצע גלובלי) הוא underfitting קיצוני. MAE=0.422, R²=-0.046.'
  },
  {
    cat: 'problem', emoji: '⚖️', name: 'Bias-Variance Tradeoff',
    kid: 'את יורה למטרה. <strong>Bias</strong> = את מכוונת כל הזמן ימינה (תמיד טועה באותו כיוון). <strong>Variance</strong> = את יורה לכל הצדדים, פעם משם פעם לכאן (לא יציבה). רוצים להוריד את שניהם, אבל בדרך כלל אם תוריד אחד — השני יעלה.',
    tech: '<code>Total Error = Bias² + Variance + Irreducible Error</code>. מודל פשוט = bias גבוה, variance נמוך. מודל מורכב = bias נמוך, variance גבוה. המטרה: למצוא נקודת מינימום של הסכום.',
    where: 'Ridge מקטין variance ע"י L2. RandomForest מקטין variance ע"י bagging. Boosting מקטין bias ע"י תיקון איטרטיבי.'
  },

  // ===== Linear Models =====
  {
    cat: 'linear', emoji: '📏', name: 'Linear Regression',
    kid: 'את מציירת קו ישר על דף עם נקודות, מנסה שיעבור הכי קרוב לכולן. הקו הזה הוא המודל. רוצים לחזות נקודה חדשה — בודקים איפה היא נופלת על הקו.',
    tech: '<code>y = w₀ + w₁x₁ + w₂x₂ + ... + wₙxₙ</code>. מוצא משקלים <code>w</code> שממזערים את <code>Σ(y - ŷ)²</code> (OLS). הנחות: ליניאריות, עצמאות שגיאות, שונות אחידה, נורמליות שאריות.',
    where: 'הבסיס לכל המודלים הליניאריים (Ridge, Lasso, ElasticNet). ב-V1 גילינו שזה לא מספיק חזק לרייטינג — היחסים לא ליניאריים.'
  },
  {
    cat: 'linear', emoji: '🛡️', name: 'Ridge Regression',
    kid: 'רגרסיה ליניארית, אבל אם משקלים נהיים גדולים מדי — המודל "מעניש" את עצמו. ככה הוא לא נהיה פרוע ומשתגע.',
    tech: 'Linear Regression + L2 penalty: <code>Loss = Σ(y-ŷ)² + α·Σw²</code>. מקטין variance במחיר עלייה קלה ב-bias. שומר על כל הפיצ\'רים אבל מקטין משקלים. פתרון אנליטי קיים.',
    where: '<strong>MAE=0.372, R²=0.471</strong>. שיפור על נאיבי, אבל לא מצליח לתפוס יחסים לא-ליניאריים. שימש כ-baseline.'
  },
  {
    cat: 'linear', emoji: '🪓', name: 'Lasso Regression',
    kid: 'כמו Ridge, אבל יותר אכזרי — אם פיצ\'ר לא חשוב, המשקל שלו יורד עד 0 לגמרי. ככה Lasso "בוחר" אילו פיצ\'רים חשובים ואילו לזרוק.',
    tech: 'Linear Regression + L1 penalty: <code>Loss = Σ(y-ŷ)² + α·Σ|w|</code>. בניגוד ל-Ridge, יכול להעמיד משקלים בדיוק על 0 → feature selection אוטומטי.',
    where: '<strong>MAE=0.288, R²=0.486</strong>. הפתיע — היה טוב יותר מ-Ridge. כנראה כי הרבה מהפיצ\'רים שלנו רעש, ו-Lasso ידע לאפס אותם.'
  },
  {
    cat: 'linear', emoji: '🔗', name: 'ElasticNet',
    kid: 'ערבוב של Ridge ו-Lasso. גם מקטין משקלים גדולים (Ridge) וגם מאפס פיצ\'רים לא חשובים (Lasso). השילוב הטוב משני העולמות.',
    tech: '<code>Loss = Σ(y-ŷ)² + α·[ρ·Σ|w| + (1-ρ)·Σw²]</code>. פרמטר <code>ρ</code> בין 0 (Ridge) ל-1 (Lasso). שימושי כשיש פיצ\'רים מתואמים — Lasso לבד יבחר רק אחד מהקבוצה, ElasticNet יחלק.',
    where: '<strong>MAE=0.294</strong>. דומה ל-Lasso. נכלל בהשוואה כסטנדרט תעשייתי.'
  },
  {
    cat: 'linear', emoji: '🎲', name: 'BayesianRidge',
    kid: 'במקום להגיד "המשקל הוא 3" — המודל אומר "אני 80% בטוח שהמשקל הוא בין 2.5 ל-3.5". הוא נותן רווח-ביטחון לכל משקל.',
    tech: 'Bayesian inference על משקלי רגרסיה — מניחים prior גאוסיאני ומחשבים posterior. מחזיר גם הערכה וגם אי-ודאות. בוחר את הרגולריזציה אוטומטית מהדאטה (אין צורך ב-α).',
    where: '<strong>MAE=0.291</strong>. דומה ל-Lasso. היתרון התיאורטי (אי-ודאות) לא נוצל בפרוייקט.'
  },
  {
    cat: 'linear', emoji: '💪', name: 'HuberRegressor',
    kid: 'רגרסיה רגילה "נבהלת" מנקודות חריגות מאוד (outliers) ומתעקמת בגללן. Huber אומר "אם הטעות גדולה מדי — אתעלם מהיקפיות שלה". יותר עמיד.',
    tech: 'משלב MSE (לטעויות קטנות) ו-MAE (לטעויות גדולות) באמצעות <code>Huber loss</code>. עד סף <code>δ</code> — ריבועי, מעבר לסף — ליניארי. עמיד ל-outliers.',
    where: '<strong>MAE=0.298</strong>. דומה למודלים ליניאריים אחרים, לא הצטיין כי outliers בדאטה שלנו (שאגת הארי) הם בדיוק מה שאנחנו רוצים <em>לא</em> להתעלם ממנו.'
  },

  // ===== Regularization =====
  {
    cat: 'reg', emoji: '1️⃣', name: 'L1 Regularization',
    kid: 'מענישים את המודל לפי <strong>סכום</strong> המשקלים. אם משקל הוא 3, העונש 3. אם 0, אין עונש. זה גורם למודל להעדיף משקלים=0 בלי לכאוב יותר מדי.',
    tech: '<code>Penalty = α·Σ|w|</code>. ההשפעה הגיאומטרית — קו עונש מרובע. הפתרון הופך לפעמים לעבור על קודקודי הריבוע → משקלים=0. מתאים לבחירת פיצ\'רים.',
    where: 'ב-Lasso ובחלק מ-ElasticNet.'
  },
  {
    cat: 'reg', emoji: '2️⃣', name: 'L2 Regularization',
    kid: 'מענישים לפי <strong>ריבוע</strong> המשקלים. אם משקל הוא 3, העונש 9. אם 1, העונש רק 1. ככה משקלים גדולים נענשים הרבה, וקטנים כמעט לא — אבל אף משקל לא יורד ל-0 לגמרי.',
    tech: '<code>Penalty = α·Σw²</code>. ההשפעה — קו עונש עגול. כל המשקלים יורדים אבל לא מתאפסים. מתאים כשכל הפיצ\'רים תורמים משהו.',
    where: 'ב-Ridge וב-MLP (weight decay).'
  },

  // ===== Trees =====
  {
    cat: 'trees', emoji: '🌲', name: 'Decision Tree',
    kid: 'משחק "20 שאלות". בכל צעד שואלים שאלת כן/לא: "האם זה יום שלישי?" → ימינה. "האם השעה אחרי 20:00?" → שמאלה. בסוף מגיעים לתחזית.',
    tech: 'מבנה היררכי של תנאי if-then-else. כל node מפצל את הדאטה לפי פיצ\'ר וסף שממקסמים information gain (סיווג) או reduction in variance (רגרסיה). עלים = ערכי חיזוי.',
    where: '<strong>MAE=0.298</strong>. בודד הוא חלש (overfitting אם עמוק, underfitting אם רדוד). אבל הוא הבסיס לכל יערות וה-Boosting.'
  },
  {
    cat: 'trees', emoji: '🛍️', name: 'Bagging',
    kid: 'במקום לשאול שכן אחד מה לעשות — שואלים 100 שכנים, וכל אחד מבסס דעתו על הסיפורים השונים ששמע. בסוף לוקחים ממוצע. ככה אפילו אם שכן אחד טועה — הממוצע יציב.',
    tech: 'מאמנים N מודלים, כל אחד על תת-מדגם רנדומלי של הדאטה (sampling with replacement). חיזוי = ממוצע (רגרסיה) או רוב (סיווג). מקטין variance.',
    where: 'הבסיס של RandomForest ו-ExtraTrees.'
  },
  {
    cat: 'trees', emoji: '🌳', name: 'Random Forest',
    kid: 'יער של עצי החלטה, וכל עץ ראה רק חלק מהדאטה וחלק מהשאלות. בסוף לוקחים ממוצע מכל העצים. אף עץ לבד לא חכם, אבל היער כן.',
    tech: 'Bagging + מבחר רנדומלי של פיצ\'רים בכל split (<code>max_features</code>). N עצים (לרוב 100-500). חיזוי = ממוצע. עמיד מאוד ל-overfitting, לא דורש scaling.',
    where: '<strong>MAE=0.280, R²=0.566</strong> (לאחר tuning). אחד המודלים הטובים שלנו. שימש כ-baseline חזק לבחינה.'
  },
  {
    cat: 'trees', emoji: '🎰', name: 'ExtraTrees',
    kid: 'כמו RandomForest, אבל בכל שאלה — במקום למצוא את השאלה הטובה ביותר, פשוט בוחרים שאלה רנדומלית! נשמע משוגע אבל זה עובד כי הרנדומליות הנוספת מקטינה overfitting.',
    tech: 'כמו RF, אבל הסף של כל split נבחר רנדומלית (לא ע"י חיפוש האופטימלי). מהיר יותר לאמן, variance נמוכה יותר, bias טיפה גבוה יותר.',
    where: '<strong>MAE=0.272, R²=0.579</strong>. הפתיע לטובה — היה טוב יותר מ-RandomForest רגיל. נכלל בהשוואה הסופית.'
  },

  // ===== Boosting =====
  {
    cat: 'boost', emoji: '⛓️', name: 'רעיון ה-Boosting',
    kid: 'במקום לבנות יער של עצים שעובדים במקביל (RandomForest), בונים שרשרת של עצים. עץ 1 חוזה משהו, עץ 2 מתקן את הטעויות של עץ 1, עץ 3 מתקן את הטעויות של עצים 1+2, וכך הלאה. כל אחד מתקן את הקודמים.',
    tech: 'Sequential ensemble. בכל איטרציה, מודל חדש מאומן לחזות את ה-residuals (שאריות הטעות) של ה-ensemble הקיים. <code>f(x) = f₀(x) + η·f₁(x) + η·f₂(x) + ...</code>. <code>η</code> = learning rate.',
    where: 'כל מודלי ה-Boosting (GB, HistGB, XGB, LGB, CatBoost) שניצחו בהשוואה.'
  },
  {
    cat: 'boost', emoji: '📈', name: 'GradientBoosting (sklearn)',
    kid: 'Boosting קלאסי. כל עץ חדש מסתכל על "כמה טעיתי" של העצים הקודמים, ומנסה לתקן בדיוק את הטעויות האלה.',
    tech: 'Boosting עם gradient descent בפונקציית loss. כל עץ מאומן על שלילי הגרדיאנט של ה-loss. פרמטרים: <code>n_estimators</code>, <code>learning_rate</code>, <code>max_depth</code>, <code>subsample</code>.',
    where: '<strong>MAE=0.270, R²=0.579</strong>. מצוין אבל איטי. הוחלף ב-HistGradientBoosting שמהיר פי 10.'
  },
  {
    cat: 'boost', emoji: '🏆', name: 'HistGradientBoosting (הזוכה!)',
    kid: 'במקום להתחשב בכל הערכים האפשריים של פיצ\'ר (יכולים להיות אלפים), הוא מחלק אותם ל-256 "סלים" (bins). הרבה יותר מהיר, ולפעמים גם מדויק יותר כי ה-binning עצמו פועל כמו רגולריזציה.',
    tech: 'GradientBoosting + histogram-based feature binning (256 bins לפי default). מהיר פי 10-100, תמיכה טבעית ב-NaN ובקטגוריות. מומלץ ע"י sklearn ל-datasets בגודל בינוני-גדול. מבוסס על LightGBM-style binning.',
    where: '<strong>🥇 הזוכה! MAE=0.263, R²=0.603</strong>. המודל בשימוש בפועל ב-<code>pages/4_🎯_חיזוי_עתידי.py</code> (טעון מ-<code>model_saved.joblib</code>).'
  },
  {
    cat: 'boost', emoji: '⚡', name: 'XGBoost',
    kid: 'Boosting "מהירים ומפוצצים". מהיר מאוד, מנצח תחרויות, יודע לעבוד עם הרבה דאטה במקביל.',
    tech: 'Extreme Gradient Boosting. שיפורים על GB קלאסי: regularization מובנה (L1+L2), טיפול חכם ב-NaN, parallelization, tree pruning. אלגוריתם של תחרויות Kaggle.',
    where: '<strong>MAE=0.280, R²=0.558</strong>. מצוין, אבל הפסיד בכמה נקודות ל-HistGB. נכלל בהשוואה כסטנדרט תעשייתי.'
  },
  {
    cat: 'boost', emoji: '💨', name: 'LightGBM',
    kid: 'Boosting קל-משקל ומהיר במיוחד. במקום שכל עץ יגדל "מאוזן" (כל הענפים), הוא מאריך רק את הענף החשוב — מהיר יותר ולפעמים מדויק יותר.',
    tech: 'Microsoft. Leaf-wise growth (במקום level-wise של XGBoost) — מאריך את העלה עם הירידה הגדולה ב-loss. Histogram binning דומה ל-HistGB. מהיר ויעיל זיכרון.',
    where: '<strong>MAE=0.265, R²=0.598</strong>. כמעט קשור עם HistGB. שימש כעדות שמתחת ההוד הם מאוד דומים.'
  },
  {
    cat: 'boost', emoji: '🐱', name: 'CatBoost',
    kid: 'Boosting שמיוחד בלהתמודד עם קטגוריות (כמו "שם תוכנית" עם 179 ערכים שונים). בלעדיו צריך לעשות One-Hot ידנית, איתו זה אוטומטי וחכם יותר.',
    tech: 'Yandex. ordered boosting (מונע target leakage בקידוד קטגוריות), טיפול אוטומטי בקטגוריות עם target statistics, symmetric trees.',
    where: '<strong>MAE=0.271, R²=0.576</strong>. בשורה אחת קוד — בלי הנדסה ידנית של קטגוריות. הוכיח שגישת auto-encoding שלו לא דרמטית יותר טוב בדאטה הזה.'
  },

  // ===== Other =====
  {
    cat: 'other', emoji: '🏘️', name: 'KNN (K-Nearest Neighbors)',
    kid: 'איך לחזות מה תרצה לאכול ביום שלישי? מסתכלים על מה אכלת ב-5 ימי שלישי האחרונים שהיו דומים (גשם / חורף / לפני אימון), ולוקחים ממוצע.',
    tech: 'Non-parametric. כדי לחזות נקודה חדשה — מוצאים K שכנים קרובים ביותר במרחב הפיצ\'רים (לפי Euclidean / Manhattan / Cosine), מחזירים ממוצע (רגרסיה) או רוב (סיווג). דורש scaling.',
    where: '<strong>MAE=0.297</strong>. סביר אבל לא מצוין. הבעיה: בדאטה רב-ממדי "השכנים" לא ממש קרובים (curse of dimensionality).'
  },
  {
    cat: 'other', emoji: '🚇', name: 'SVR (Support Vector Regression)',
    kid: 'מצייר "צינור" סביב הנקודות שמרבית הנקודות בתוכו. נקודות בתוך הצינור לא נחשבות טעות. רק נקודות מחוצה — נחשבות.',
    tech: 'הרחבה של SVM לרגרסיה. מוצא פונקציה שמרבית הנקודות בתוך <code>ε-tube</code> סביבה. עם kernel (RBF, linear, poly) יכול לתפוס יחסים לא-ליניאריים. דורש scaling.',
    where: '<strong>MAE=0.294</strong>. דומה לליניאריים. הוסבר חלקית כי dataset שלנו לא ענק (10K שורות) ולא נדרש kernel trick מורכב.'
  },
  {
    cat: 'other', emoji: '🧠', name: 'MLP (Neural Network)',
    kid: 'דמיין שכבות של "סוכנים קטנים". סוכן בשכבה 1 מסתכל על הקלט, מחליט משהו, מעביר לשכבה 2. שם סוכנים אחרים מסתכלים על מה ששכבה 1 אמרה, מחליטים משהו אחר, מעבירים הלאה. בסוף השכבה האחרונה נותנת תחזית.',
    tech: 'Feed-forward Neural Network. שכבות של neurons עם פונקציות הפעלה (ReLU, sigmoid, tanh). מאומנת ע"י backpropagation עם gradient descent. בפרוייקט: <code>hidden_layer_sizes=(64, 32)</code>.',
    where: '<strong>MAE=0.328, R²=0.468</strong>. לא הצטיין. נוירונים זקוקים להמון דאטה (מאות אלפים+), 10K שורות לא מספיק. עצים מנצחים בדאטה טבלאי קטן-בינוני.'
  },

  // ===== Ensembles =====
  {
    cat: 'ensemble', emoji: '🎭', name: 'רעיון ה-Ensemble',
    kid: 'במקום לבקש דעה ממומחה אחד — מבקשים מ-3 מומחים שונים, ולוקחים ממוצע. אם רופא אומר "כן", מהנדס "לא" וכלכלן "כן" — לוקחים "כן" אבל פחות בטוחים. בדרך כלל ממוצע של מומחים יותר מדויק מכל מומחה לבד.',
    tech: 'שילוב חיזויי מודלים שונים. סוגים: averaging, voting, stacking, bagging, boosting. מקטין variance ולעיתים גם bias. עובד הכי טוב כשהמודלים שונים זה מזה (decorrelated).',
    where: 'הוספנו Stacking לרשימה. בפועל המודל הזוכה היה יחיד — Stacking לא נתן יתרון מובהק על HistGB לבד.'
  },
  {
    cat: 'ensemble', emoji: '🏛️', name: 'Stacking',
    kid: 'קודם 4 מומחים נותנים תחזית. אחר כך, יש "סופר-מומחה" שלא מסתכל על הדאטה המקורי אלא רק על 4 התחזיות, ולומד מי מהמומחים לסמוך עליו בכל מצב. הוא לא לוקח ממוצע פשוט — הוא חכם יותר.',
    tech: 'N base models מאומנים. החיזויים שלהם הופכים לפיצ\'רים של meta-model שמאומן עליהם (לרוב Ridge / Linear). חשוב — base models מאומנים ב-CV כדי למנוע leakage.',
    where: 'Stacking של RF+XGB+LGB+Ridge → meta=Ridge. <strong>MAE=0.272, R²=0.566</strong>. לא ניצח את HistGB יחיד — הקורלציה בין מודלי boosting גבוהה, אין הרבה מה להרוויח מ-stacking ביניהם.'
  },

  // ===== Calibration =====
  {
    cat: 'calib', emoji: '📊', name: 'Confidence Interval',
    kid: 'במקום להגיד "התחזית היא 3.5" — אומרים "בטוח 80% שהתחזית בין 2.9 ל-4.1". זה רווח-ביטחון. ככל שהוא צר יותר, אנחנו בטוחים יותר.',
    tech: 'טווח שמכסה את ה-true value בהסתברות נתונה (e.g., 80%, 95%). חישוב לעיתים מבוסס על quantile regression / bootstrap / נתוני residual היסטוריים.',
    where: 'ב-<code>utils/predict.py</code>: P10/P90 של רייטינג היסטורי באותה תוכנית×רצועה. מינימום ±0.4 לחג, ±0.6 לאירוע ביטחוני. מוצג כ"רווח: 2.05 - 2.65" ליד החיזוי.'
  },
  {
    cat: 'calib', emoji: '📈', name: 'Trend Correction',
    kid: 'אם הילד שלך גדל 1 ס"מ בחודש, ואת רוצה לדעת כמה הוא יהיה בעוד 3 חודשים — תוסיפי 3 ס"מ לגובה הנוכחי. אם תחזיותיך לא לוקחות בחשבון את הגדילה, תטעי כל פעם.',
    tech: 'רגרסיה ליניארית על העבר הקרוב (6 חודשים אחרונים) כדי לחלץ slope (שינוי לחודש). מיישמים על החיזוי הבסיסי לפי המרחק מ-"היום". מוגבל ל-±5%/חודש למניעת אקסטרפולציה מטורפת.',
    where: '<code>compute_recent_trend()</code> ב-<code>utils/predict.py</code>. תוקן אחרי שגילינו שתחזית של חודשיים-קדימה הייתה +20% (לא ריאלי). כעת capped ל-±5%/חודש.'
  },
  {
    cat: 'calib', emoji: '↔️', name: 'Bias Correction',
    kid: 'אם תמיד טעית 0.2 למטה (יצא לך 3.0 כשהאמת 3.2), פשוט תוסיפי 0.2 לכל התחזיות הבאות שלך.',
    tech: 'ממצעים את ה-residual המערכתי על סט בחינה ומוסיפים לחיזויים חדשים. עוזר כשהמודל miscalibrated באופן עקבי.',
    where: 'לא בפועל — המודל שלנו רק מעט בעל הטיה. החלטנו לא להוסיף לפי שזה מסבך תחזוקה.'
  },

  // ===== Infra =====
  {
    cat: 'infra', emoji: '🔗', name: 'Pipeline (scikit-learn)',
    kid: 'רצף של פעולות שמופעלות בסדר. קודם מילוי חסרים → אחר כך scaling → אחר כך one-hot → אחר כך מודל. במקום לעשות כל צעד ידנית, מגדירים pipeline אחד ומפעילים <code>fit</code>+<code>predict</code>.',
    tech: '<code>sklearn.pipeline.Pipeline</code> או <code>make_pipeline</code>. שרשרת transformer-ים שמסתיימת ב-estimator. מבטיח שאותם transformer-ים יופעלו על train ועל test (מונע leakage). תומך ב-CV.',
    where: '<code>train_and_save_model.py</code> בונה Pipeline: <code>ColumnTransformer(imputer + scaler + encoder) → HistGradientBoosting</code>, ושומר את הכל ב-joblib.'
  },
  {
    cat: 'infra', emoji: '💾', name: 'joblib (serialization)',
    kid: 'איך שומרים מודל מאומן בקובץ כדי להשתמש בו אחר כך בלי לאמן מחדש? כותבים אותו לקובץ בינארי. זה joblib.',
    tech: 'ספריית Python לעריצת אובייקטים (pickle משופר). מהיר במיוחד למערכים גדולים (numpy arrays) כי שומר them efficient. דורש זהירות עם class definitions — class שמוגדר ב-script A לא ניתן לטעון מ-script B אלא אם החתימה זהה.',
    where: '<code>model_saved.joblib</code> (1.2MB) — נוצר ב-<code>train_and_save_model.py</code>, נטען ב-<code>utils/predict.py</code>. הבעיה: <code>_SimpleMedianImputer</code> המקורי הוגדר ב-script הראשי → נכשל בטעינה מ-Streamlit. הפתרון: העברה ל-<code>utils/imputers.py</code> משותף.'
  },
  {
    cat: 'infra', emoji: '⚡', name: 'Streamlit Caching',
    kid: 'אם פעם ראשונה לקחת 5 שניות לטעון קובץ של 50MB, אתה לא רוצה לחכות 5 שניות בכל ריענון של הדף. שומרים את התוצאה בזיכרון. בפעם הבאה — 0.01 שניות.',
    tech: '<code>@st.cache_data</code> עוטף פונקציה כך שהתוצאה נשמרת לפי פרמטרים. רענון רק כשהפרמטרים משתנים או כש-TTL פג. <code>@st.cache_resource</code> למבני נתונים גלובליים (מודל מאומן).',
    where: 'ב-<code>utils/data_loader.py</code> — <code>@st.cache_data</code> על טעינת xlsx. ב-<code>utils/predict.py</code> — <code>@st.cache_resource</code> על טעינת המודל מ-joblib (טוען פעם אחת, משמש בכל החיזויים).'
  },
  {
    cat: 'infra', emoji: '📑', name: 'Streamlit Multi-Page',
    kid: 'במקום אפליקציה ענקית עם מסך אחד וכפתורים — מחלקים לדפים. כל קובץ ב-<code>pages/</code> הופך לדף בתפריט הצדדי. ככה האפליקציה מאורגנת.',
    tech: 'Streamlit מזהה אוטומטית כל קובץ <code>pages/*.py</code> ובונה sidebar navigation. שם הקובץ קובע את שם הדף ב-UI. אפשר להוסיף emoji בשם הקובץ → מופיע בתפריט.',
    where: '4 דפים: <code>1_📊_חיזויים</code>, <code>2_📺_כרטיס_תוכנית</code>, <code>3_🔍_השוואת_מודלים</code>, <code>4_🎯_חיזוי_עתידי</code>. <code>app.py</code> הוא הדף הראשי.'
  },
  {
    cat: 'infra', emoji: '↩️', name: 'RTL ב-Streamlit',
    kid: 'אנגלית קוראים משמאל לימין. עברית הפוך — מימין לשמאל. צריך להגיד לדפדפן לסדר הכל הפוך.',
    tech: 'Streamlit לא תומך RTL native. הפתרון: CSS injection דרך <code>st.markdown(unsafe_allow_html=True)</code> שמגדיר <code>direction: rtl</code> ו-<code>text-align: right</code> על container הראשי.',
    where: '<code>utils/style.py</code> → <code>apply_style()</code> — מזריק CSS שכולל RTL + Heebo font + גרדיאנטים + hover effects. נקרא בתחילת כל דף.'
  },
  {
    cat: 'infra', emoji: '🔐', name: 'Streamlit Secrets',
    kid: 'סיסמאות לא שמים בקוד שכולם רואים. שמים אותן בקובץ נפרד שרק השרת רואה.',
    tech: '<code>.streamlit/secrets.toml</code> — קובץ TOML עם משתני סודות. נקראים ב-Python כ-<code>st.secrets["KEY"]</code>. ב-Streamlit Cloud מגדירים אותם ב-dashboard, לא בקוד.',
    where: '<code>utils/auth.py</code> → <code>st.secrets["APP_PASSWORD"]</code> עבור password gate. הקובץ <code>.streamlit/secrets.toml</code> ב-<code>.gitignore</code>.'
  },
  {
    cat: 'infra', emoji: '☁️', name: 'Cloud Deployment',
    kid: 'איך לקחת אפליקציה במחשב שלי ולתת לכל העולם גישה? מעלים לשרת בענן. הוא רץ שם 24/7 וכל אחד יכול להיכנס לדפדפן.',
    tech: '<strong>Streamlit Cloud:</strong> מארח אפליקציות Streamlit ישירות מ-GitHub repo. CI/CD אוטומטי בכל push. <strong>GitHub Pages:</strong> מארח אתרים סטטיים (HTML/CSS/JS) חינם מ-GitHub repo. מתאים לאתרי תיק עבודות.',
    where: '<strong>Streamlit Cloud:</strong> <code>https://i24-ratings-orit.streamlit.app</code>. <strong>GitHub Pages:</strong> בתהליך — דף הנחיתה הזה!'
  },
];
