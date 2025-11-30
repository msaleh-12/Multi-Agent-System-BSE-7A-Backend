import React, { useState } from 'react';

// --- Type Definitions (Must match backend/models.py) ---
interface SubjectDetail { name: string; difficulty: string; }
interface Deadline { subject: string; exam_date: string; }
interface PerformanceFeedback { AI: string; OS: string; SPM: string; }
interface Availability { preferred_days: string[]; preferred_times: string[]; daily_study_limit_hours: number; }
interface AgentInput {
    student_id: string;
    profile: { subjects: SubjectDetail[] };
    availability: Availability;
    deadlines: Deadline[];
    performance_feedback: PerformanceFeedback;
    context: { request_type: string; priority: string };
}
interface RecommendedSession { day: string; subject: string; time: string; }
interface ScheduleSummary { total_sessions: number; total_study_hours: number; coverage_percentage: string; next_revision_day: string; }
interface AdaptiveAction { trigger: string; adjustment: string; }
interface Reminder { type: string; message: string; }
interface ReportSummary { consistency_score: number; time_efficiency: string; performance_trend: string; }
interface AgentOutput {
    student_id: string;
    schedule_summary: ScheduleSummary;
    recommended_schedule: RecommendedSession[];
    adaptive_actions: AdaptiveAction[];
    reminders: Reminder[];
    report_summary: ReportSummary;
}

// --- Configuration ---
const BACKEND_URL = 'http://127.0.0.1:8000/generate_schedule/';

// Pre-filled data using the example provided
const initialInput: AgentInput = {
    "student_id": "STU_2459",
    "profile": {
        "subjects": [
            { "name": "Artificial Intelligence", "difficulty": "high" },
            { "name": "Operating Systems", "difficulty": "medium" },
            { "name": "Software Project Management", "difficulty": "low" }
        ]
    },
    "availability": {
        "preferred_days": ["Monday", "Tuesday", "Wednesday", "Friday"],
        "preferred_times": ["6:00 PM", "9:00 PM"],
        "daily_study_limit_hours": 3
    },
    "deadlines": [
        { "subject": "Artificial Intelligence", "exam_date": "2025-10-25" },
        { "subject": "Operating Systems", "exam_date": "2025-10-28" }
    ],
    "performance_feedback": {
        "AI": "weak",
        "OS": "average",
        "SPM": "strong"
    },
    "context": {
        "request_type": "generate_study_schedule",
        "priority": "high"
    }
};

// Helper function to map session list into groups by day
const groupScheduleByDay = (schedule: RecommendedSession[]) => {
    return schedule.reduce((acc, session) => {
        if (!acc[session.day]) {
            acc[session.day] = [];
        }
        acc[session.day].push(session);
        return acc;
    }, {} as Record<string, RecommendedSession[]>);
};

const App: React.FC = () => {
    const [outputData, setOutputData] = useState<AgentOutput | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    // Initial input setup
    const initialInputString = JSON.stringify(initialInput, null, 2);
    const [inputJsonText, setInputJsonText] = useState<string>(initialInputString);

    const handleGenerateSchedule = async () => {
        setIsLoading(true);
        setError(null);
        setOutputData(null);
        
        try {
            const parsedInput: AgentInput = JSON.parse(inputJsonText);

            const response = await fetch(BACKEND_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(parsedInput),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
            }

            const data: AgentOutput = await response.json();
            setOutputData(data);

        } catch (err: any) {
            console.error("Scheduling Agent Error:", err);
            setError(`Failed to generate schedule. Error: ${err.message || "Could not connect to backend."}`);
        } finally {
            setIsLoading(false);
        }
    };

    const renderSchedule = () => {
        if (!outputData) return null;

        const scheduleByDay = groupScheduleByDay(outputData.recommended_schedule);
        const daysOrder = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
        
        // Determine subjects allocated 2 hours (high priority)
        const highPrioritySubjects = outputData.recommended_schedule
            .filter(s => s.time.includes('2 hours') || s.time.includes('08:00 PM'))
            .map(s => s.subject);

        return (
            <div className="space-y-10">
                <h2 className="text-3xl font-extrabold text-indigo-900 border-b-4 border-indigo-200 pb-4">Generated Study Plan</h2>
                
                {/* 1. Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <SummaryCard title="Total Sessions" value={outputData.schedule_summary.total_sessions} icon="📚" gradient="from-indigo-500 to-indigo-700" />
                    <SummaryCard title="Total Hours" value={`${outputData.schedule_summary.total_study_hours} hrs`} icon="🕰️" gradient="from-emerald-500 to-emerald-700" />
                    <SummaryCard title="Coverage Goal" value={outputData.schedule_summary.coverage_percentage} icon="🎯" gradient="from-yellow-500 to-yellow-700" />
                    <SummaryCard title="Next Revision" value={outputData.schedule_summary.next_revision_day} icon="➡️" gradient="from-rose-500 to-rose-700" />
                </div>

                {/* 2. Recommended Schedule (Grouped by Day Timeline) */}
                <div className="bg-white p-6 rounded-2xl shadow-2xl border border-gray-100">
                    <h3 className="text-2xl font-bold mb-6 text-gray-800 border-b pb-3">Weekly Timeline Breakdown</h3>
                    <div className="space-y-6">
                        {daysOrder.map(day => {
                            const sessions = scheduleByDay[day];
                            if (!sessions || sessions.length === 0) {
                                return (
                                    <div key={day} className="flex justify-between items-center p-3 text-sm rounded-xl bg-gray-50 border border-gray-200">
                                        <span className="font-bold text-gray-500 w-1/4">{day}</span>
                                        <span className="text-gray-400 italic">No Sessions Planned</span>
                                        <span className="text-sm font-medium text-gray-400">0 hrs</span>
                                    </div>
                                );
                            }
                            return (
                                <div key={day} className="p-4 border-l-4 border-indigo-600 bg-indigo-50 rounded-xl shadow-md">
                                    <h4 className="font-extrabold text-xl mb-3 text-indigo-700">{day}</h4>
                                    <div className="space-y-3">
                                        {sessions.map((session, index) => {
                                            const isHighPriority = highPrioritySubjects.includes(session.subject);
                                            return (
                                                <div key={index} className={`flex justify-between items-center p-3 rounded-lg border-2 transition duration-150 ease-in-out ${isHighPriority ? 'bg-rose-100 border-rose-400 shadow-inner' : 'bg-white border-emerald-300 shadow-sm'}`}>
                                                    <span className={`font-semibold w-1/3 ${isHighPriority ? 'text-rose-800' : 'text-emerald-700'}`}>
                                                        {session.subject}
                                                    </span>
                                                    <span className="text-sm text-gray-600 w-1/3 text-center font-mono">
                                                        {session.time}
                                                    </span>
                                                    {isHighPriority ? (
                                                        <span className="text-xs font-bold text-white bg-rose-600 px-2.5 py-1 rounded-full shadow-md">
                                                            High Priority
                                                        </span>
                                                    ) : (
                                                        <span className="text-xs font-bold text-emerald-800 bg-emerald-200 px-2.5 py-1 rounded-full">
                                                            Review
                                                        </span>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                    <p className='mt-6 text-xs italic text-gray-500'>
                        *Note on time allocation: Multiple sessions scheduled on the same preferred time slot indicate back-to-back study blocks. The prototype's time label is simplified for display.*
                    </p>
                </div>

                {/* 3. Adaptive Actions & Performance Report */}
                <div className="grid md:grid-cols-2 gap-8">
                    <InfoBlock title="Adaptive Agent Rules" icon="🤖" gradient="from-blue-100 to-blue-200">
                        <ul className="list-disc list-inside space-y-3 text-sm text-gray-700">
                            {outputData.adaptive_actions.map((action, index) => (
                                <li key={index} className='pl-1'>
                                    <strong className="text-blue-700 font-bold">{action.trigger}:</strong> {action.adjustment}
                                </li>
                            ))}
                        </ul>
                    </InfoBlock>
                    
                    <InfoBlock title="Performance & Feedback" icon="📊" gradient="from-green-100 to-green-200">
                        <div className="space-y-3 text-sm text-gray-700">
                            <div className='flex justify-between items-center'>
                                <strong>Consistency Score:</strong> <Badge value={outputData.report_summary.consistency_score} />
                            </div>
                            <div className='flex justify-between items-center'>
                                <strong>Time Efficiency:</strong> <Badge value={outputData.report_summary.time_efficiency} />
                            </div>
                            <div className='flex justify-between items-center'>
                                <strong>Performance Trend:</strong> <Badge value={outputData.report_summary.performance_trend} />
                            </div>
                            <div className="pt-3 border-t mt-3 border-gray-200">
                                <h4 className="font-bold text-gray-800 mb-1 flex items-center gap-2">
                                    <span className='text-xl'>🔔</span> Agent Reminders:
                                </h4>
                                {outputData.reminders.map((r, i) => (
                                    <p key={i} className="text-xs italic text-gray-600 pl-1">- {r.message}</p>
                                ))}
                            </div>
                        </div>
                    </InfoBlock>
                </div>
            </div>
        );
    };

    return (
        <div className="min-h-screen bg-gray-50 p-4 sm:p-10 font-sans">
            <style>{`
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
                body { font-family: 'Inter', sans-serif; }
            `}</style>
            <div className="max-w-7xl mx-auto">
                <header className="text-center mb-12">
                    <h1 className="text-5xl font-extrabold text-gray-900 mb-3">Study Scheduler Agent</h1>
                    <p className="text-xl text-gray-600">The Adaptive Study Planning Prototype (Section A)</p>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-5 gap-10">
                    
                    {/* Input Panel (Takes 2/5ths of the space, now sticky) */}
                    <div className="lg:col-span-2 bg-white p-6 rounded-2xl shadow-xl h-fit sticky top-6 border-4 border-indigo-100/50">
                        <h2 className="text-2xl font-bold mb-4 text-gray-800 border-b pb-3">Input Contract (JSON Payload)</h2>
                        <textarea
                            className="w-full h-96 p-4 border-2 border-gray-300 rounded-lg bg-gray-50 text-sm font-mono focus:ring-indigo-500 focus:border-indigo-500 transition duration-150 resize-none"
                            value={inputJsonText}
                            onChange={(e) => setInputJsonText(e.target.value)}
                            spellCheck="false"
                        />
                        <button
                            onClick={handleGenerateSchedule}
                            disabled={isLoading}
                            className={`w-full mt-4 px-6 py-3 text-white font-extrabold rounded-xl transition duration-300 transform hover:scale-[1.01] flex items-center justify-center ${
                                isLoading
                                    ? 'bg-indigo-400 cursor-not-allowed'
                                    : 'bg-indigo-700 hover:bg-indigo-800 shadow-2xl hover:shadow-3xl'
                            }`}
                        >
                            {isLoading ? (
                                <span className="flex items-center">
                                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Generating Schedule...
                                </span>
                            ) : (
                                'Generate Schedule'
                            )}
                        </button>

                        {error && (
                            <div className="mt-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg shadow-inner">
                                <strong className='font-bold'>API Error:</strong> {error}
                            </div>
                        )}
                    </div>
                    
                    {/* Output Panel (Takes 3/5ths of the space) */}
                    <div className="lg:col-span-3 bg-gray-100 p-8 rounded-2xl shadow-inner-2xl border border-gray-200">
                        {!outputData && !isLoading && (
                            <div className="h-full min-h-[400px] flex items-center justify-center text-center text-gray-500 p-10 border-4 border-dashed border-indigo-400 rounded-xl">
                                <p className="text-xl font-medium space-y-2">
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-12 h-12 mx-auto text-indigo-500 animate-pulse">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75M6.75 6h.008v.008H6.75ZM9.75 6h.008v.008H9.75ZM12.75 6h.008v.008H12.75Z" />
                                    </svg>
                                    <span>Schedule Agent Awaiting Request</span>
                                    <br/>
                                    <small className="text-sm block">Click **Generate Schedule** to start the planning process.</small>
                                </p>
                            </div>
                        )}
                        
                        {outputData && renderSchedule()}
                    </div>
                </div>
            </div>
        </div>
    );
};

// --- Helper Components for Aesthetics ---

const SummaryCard: React.FC<{ title: string; value: string | number; icon: string; gradient: string }> = ({ title, value, icon, gradient }) => (
    <div className={`p-4 rounded-xl shadow-lg border border-gray-100 bg-gradient-to-br ${gradient} text-white transition duration-300 hover:shadow-2xl`}>
        <div className='flex items-center gap-2 mb-1'>
            <span className='text-xl'>{icon}</span>
            <p className="text-sm font-medium opacity-90">{title}</p>
        </div>
        <p className={`text-3xl font-extrabold mt-1 drop-shadow-md`}>{value}</p>
    </div>
);

const InfoBlock: React.FC<{ title: string; icon: string; gradient: string; children: React.ReactNode }> = ({ title, icon, gradient, children }) => (
    <div className={`p-6 rounded-2xl shadow-xl border border-gray-200 bg-gradient-to-b ${gradient}`}>
        <h3 className="text-xl font-bold mb-4 text-gray-800 flex items-center gap-2 border-b border-gray-300 pb-2">
            <span className='text-2xl'>{icon}</span> {title}
        </h3>
        {children}
    </div>
);

const Badge: React.FC<{ value: string | number }> = ({ value }) => {
    let bgColor = 'bg-gray-200';
    let textColor = 'text-gray-800';
    let displayValue = String(value);

    // Dynamic styling based on value or keywords
    if (value === 'High' || value === 'Improving' || Number(value) >= 80) {
        bgColor = 'bg-emerald-500';
        textColor = 'text-white';
        displayValue = typeof value === 'string' ? value : `${value}%`;
    } else if (value === 'average' || value === 'Balanced' || (Number(value) > 60 && Number(value) < 80)) {
        bgColor = 'bg-yellow-500';
        textColor = 'text-gray-800';
        displayValue = typeof value === 'string' ? value : `${value}%`;
    } else if (value === 'weak' || value === 'Low' || Number(value) < 60) {
         bgColor = 'bg-rose-500';
        textColor = 'text-white';
        displayValue = typeof value === 'string' ? value : `${value}%`;
    }

    return (
        <span className={`inline-block px-3 py-1 text-xs font-extrabold rounded-full ${bgColor} ${textColor} shadow-md`}>
            {displayValue}
        </span>
    );
};

export default App;