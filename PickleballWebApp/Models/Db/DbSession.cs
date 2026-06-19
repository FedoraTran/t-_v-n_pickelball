using System;
using System.Collections.Generic;
using Supabase.Postgrest.Attributes;
using Supabase.Postgrest.Models;

namespace PickleballWebApp.Models.Db
{
    [Table("sessions")]
    public class DbSession : BaseModel
    {
        [PrimaryKey("id", false)]
        public Guid Id { get; set; }

        [Column("user_id")]
        public Guid UserId { get; set; }

        [Column("preset_name")]
        public string PresetName { get; set; } = string.Empty;

        [Column("mode")]
        public string Mode { get; set; } = "camera";

        [Column("overall_accuracy")]
        public double OverallAccuracy { get; set; }

        [Column("num_frames")]
        public int NumFrames { get; set; }

        [Column("duration_sec")]
        public double DurationSec { get; set; }

        [Column("feedback")]
        public List<string> Feedback { get; set; } = new();

        [Column("per_joint")]
        public List<double?> PerJoint { get; set; } = new();

        [Column("video_url")]
        public string? VideoUrl { get; set; }

        [Column("report_url")]
        public string? ReportUrl { get; set; }

        [Column("created_at")]
        public DateTime CreatedAt { get; set; }
    }
}
