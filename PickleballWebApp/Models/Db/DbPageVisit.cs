using System;
using Supabase.Postgrest.Attributes;
using Supabase.Postgrest.Models;

namespace PickleballWebApp.Models.Db
{
    [Table("page_visits")]
    public class DbPageVisit : BaseModel
    {
        [PrimaryKey("id", true)]
        public long Id { get; set; }

        [Column("user_id")]
        public Guid UserId { get; set; }

        [Column("page_path")]
        public string PagePath { get; set; } = string.Empty;

        [Column("page_title")]
        public string PageTitle { get; set; } = string.Empty;

        [Column("visited_at")]
        public DateTime VisitedAt { get; set; }
    }
}
