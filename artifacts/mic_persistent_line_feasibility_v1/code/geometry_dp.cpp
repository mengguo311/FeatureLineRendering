#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

// Seven states: diagonal, horizontal runs 1/2/3, vertical runs 1/2/3.
// This computes the frozen bounded-run monotone alignment, without image access.
extern "C" int bounded_dtw(const double* cost, int n, int m, int* rows, int* cols) {
    const double inf = std::numeric_limits<double>::infinity();
    std::vector<double> d(n*m*7, inf);
    std::vector<int> prev(n*m*7, -1);
    auto offset = [m](int i,int j,int s) { return (i*m+j)*7+s; };
    for(int i=0;i<n;++i) for(int j=0;j<m;++j) {
        double c=cost[i*m+j];
        if(!std::isfinite(c)) continue;
        if(i==0 && j==0) { d[0]=c; continue; }
        auto best = [&](int ni,int nj,int state,const int* allowed,int count) {
            double v=inf; int ps=-1;
            for(int a=0;a<count;++a) {
                int q=offset(ni,nj,allowed[a]);
                if(d[q]<v) { v=d[q]; ps=allowed[a]; }
            }
            int q=offset(i,j,state); d[q]=v+c; prev[q]=ps;
        };
        if(i>0 && j>0) { int a[]={0,1,2,3,4,5,6}; best(i-1,j-1,0,a,7); }
        if(j>0) {
            int a[]={0,4,5,6}; best(i,j-1,1,a,4);
            int b[]={1}; best(i,j-1,2,b,1);
            int c[]={2}; best(i,j-1,3,c,1);
        }
        if(i>0) {
            int a[]={0,1,2,3}; best(i-1,j,4,a,4);
            int b[]={4}; best(i-1,j,5,b,1);
            int c[]={5}; best(i-1,j,6,c,1);
        }
    }
    int i=n-1,j=m-1,state=0;
    for(int s=1;s<7;++s) if(d[offset(i,j,s)]<d[offset(i,j,state)]) state=s;
    if(!std::isfinite(d[offset(i,j,state)])) return 0;
    int count=0;
    while(true) {
        rows[count]=i; cols[count]=j; ++count;
        if(i==0 && j==0) break;
        int old=state; state=prev[offset(i,j,state)];
        if(state<0) return 0;
        if(old==0) { --i; --j; }
        else if(old<4) --j;
        else --i;
    }
    std::reverse(rows,rows+count); std::reverse(cols,cols+count);
    return count;
}
