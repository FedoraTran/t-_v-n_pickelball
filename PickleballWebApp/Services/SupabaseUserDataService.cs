using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using PickleballWebApp.Models;
using PickleballWebApp.Models.Db;
using Supabase.Postgrest;

namespace PickleballWebApp.Services
{
    public class SupabaseUserDataService
    {
        private readonly Supabase.Client _supabase;
        private const int MaxVisitsStored = 100;

        public SupabaseUserDataService(Supabase.Client supabase)
        {
            _supabase = supabase;
        }

        // ──────── SESSION MANAGEMENT ────────

        public async Task SaveSessionAsync(Guid userId, SessionResult session)
        {
            var dbSession = new DbSession
            {
                UserId          = userId,
                PresetName      = session.PresetName,
                Mode            = session.Mode,
                OverallAccuracy = session.OverallAccuracy,
                NumFrames       = session.NumFrames,
                DurationSec     = session.DurationSec,
                Feedback        = session.Feedback,
                PerJoint        = session.PerJointAccuracy,
                CreatedAt       = DateTime.UtcNow
            };

            await _supabase.From<DbSession>().Insert(dbSession);
        }

        public async Task<List<SessionResult>> GetSessionsAsync(Guid userId, int limit = 50)
        {
            var result = await _supabase.From<DbSession>()
                .Where(s => s.UserId == userId)
                .Order(s => s.CreatedAt, Constants.Ordering.Descending)
                .Limit(limit)
                .Get();

            return result.Models.Select(s => new SessionResult
            {
                Id                = s.Id.ToString(),
                CreatedAt         = s.CreatedAt,
                Username          = "",  // Lấy riêng nếu cần
                PresetName        = s.PresetName,
                Mode              = s.Mode,
                OverallAccuracy   = s.OverallAccuracy,
                NumFrames         = s.NumFrames,
                DurationSec       = s.DurationSec,
                Feedback          = s.Feedback,
                PerJointAccuracy  = s.PerJoint,
                VideoUrl          = s.VideoUrl,
                ReportUrl         = s.ReportUrl,
            }).ToList();
        }

        public async Task<UserStats> GetStatsAsync(Guid userId)
        {
            var sessions = await GetSessionsAsync(userId, 200);
            if (sessions.Count == 0) return new UserStats();

            var accuracies = sessions.Select(s => s.OverallAccuracy).ToList();
            return new UserStats
            {
                TotalSessions   = sessions.Count,
                AverageAccuracy = Math.Round(accuracies.Average(), 1),
                BestAccuracy    = Math.Round(accuracies.Max(), 1),
                LastSessionAt   = sessions.Max(s => s.CreatedAt),
                RecentTrend     = ComputeTrend(sessions)
            };
        }

        // ──────── PAGE VISIT TRACKING ────────

        public async Task RecordPageVisitAsync(Guid userId, string path, string title)
        {
            var visit = new DbPageVisit
            {
                UserId    = userId,
                PagePath  = path,
                PageTitle = title,
                VisitedAt = DateTime.UtcNow
            };
            await _supabase.From<DbPageVisit>().Insert(visit);
            // Việc trim 100 visits đã có trigger ở Supabase lo
        }

        public async Task<List<PageVisit>> GetRecentVisitsAsync(Guid userId, int count = 20)
        {
            var result = await _supabase.From<DbPageVisit>()
                .Where(v => v.UserId == userId)
                .Order(v => v.VisitedAt, Constants.Ordering.Descending)
                .Limit(count)
                .Get();

            return result.Models.Select(v => new PageVisit
            {
                VisitedAt = v.VisitedAt,
                PagePath  = v.PagePath,
                PageTitle = v.PageTitle
            }).ToList();
        }

        // ──────── HELPERS ────────

        private static double ComputeTrend(List<SessionResult> sessions)
        {
            if (sessions.Count < 4) return 0;
            var sorted = sessions.OrderBy(s => s.CreatedAt).ToList();
            var half = sorted.Count / 2;
            var older = sorted.Take(half).Average(s => s.OverallAccuracy);
            var newer = sorted.Skip(half).Average(s => s.OverallAccuracy);
            return Math.Round(newer - older, 1);
        }
    }
}
