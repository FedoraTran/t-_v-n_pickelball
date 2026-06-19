using System.Threading.Tasks;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc.RazorPages;
using PickleballWebApp.Extensions;
using PickleballWebApp.Models;
using PickleballWebApp.Services;

namespace PickleballWebApp.Pages
{
    [Authorize]
    public class MyProgressModel : PageModel
    {
        private readonly SupabaseUserDataService _userData;

        public MyProgressModel(SupabaseUserDataService userData)
        {
            _userData = userData;
        }

        public UserStats Stats { get; private set; } = new();
        public List<SessionResult> RecentSessions { get; private set; } = new();
        public List<PageVisit> RecentVisits { get; private set; } = new();

        public async Task OnGetAsync()
        {
            var userId = User.GetSupabaseUserId();
            Stats          = await _userData.GetStatsAsync(userId);
            RecentSessions = await _userData.GetSessionsAsync(userId, 20);
            RecentVisits   = await _userData.GetRecentVisitsAsync(userId, 15);
        }
    }
}
