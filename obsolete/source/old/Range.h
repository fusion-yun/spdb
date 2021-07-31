//
// Created by salmon on 17-1-1.
//

#ifndef SIMPLA_RANGE_H
#define SIMPLA_RANGE_H

#include <cstddef>
#include <functional>
#include <iterator>
#include <memory>
#include "Utility.h"
namespace sp {

/** @ingroup concept */

/** @ingroup concept */
/**
 * @brief a type whose instances can be split into two pieces;     *
 * @details
 * ## Summary
 *
 *  @ref tbb::splittable
 *
 *  @ref [ https://software.intel.com/zh-cn/node/506141 ]
 *
 * ## Requirements
 *  Class \c R implementing the concept of Splittable must define:
 *	Pseudo-Signature                              | Semantics
 * ---------------------------------------------- |----------
 *  \code R::R( const R& );              \endcode |Copy constructor
 *  \code R::~R();                       \endcode |Destructor
 *  \code bool R::is_divisible() const;  \endcode |True if range can be partitioned into two subranges
 *  \code bool R::empty() const;         \endcode |True if range is empty
 *  \code R::R( R& r, split );           \endcode |Split range \c r into two subranges.
 *
 * ## Description
 * > _from TBB_
 * >
 * >   A type is splittable if it has a splitting constructor that allows
 * >  an instance to be split into two pieces. The splitting constructor
 * >  takes as arguments a reference to the original object, and a dummy
 * >   argument of type split, which is defined by the library. The dummy
 * >   argument distinguishes the splitting constructor from a copy constructor.
 * >   After the constructor runs, x and the newly constructed object should
 * >   represent the two pieces of the original x. The library uses splitting
 * >    constructors in two contexts:
 * >    - Partitioning a entity_id_range into two subranges that can be processed concurrently.
 * >    - Forking a body (function object) into two bodies that can run concurrently.
 *
 * - Split  @ref Container  into two part, that can be accessed concurrently
 * - if X::left() and X::right() exists, construct proportion with the
 * ratio specified by left() and right(). (alter from tbb::proportional_split)
 *
 */
struct Splittable {
    Splittable(Splittable&, tags::split) {}

    ~Splittable() {}

    virtual bool is_divisible() = 0;

    virtual bool empty() = 0;
};
/**
 * @brief Range concept
 *   @ref https://github.com/ericniebler/range-v3
 *   @ref TBB Range concept https://software.intel.com/en-us/node/506143
 *
 *   - lightweight
 *   - non-owning
 *   - range may/may not be iteraterable (begin,end may not be defined)
 *   - range may/may not be splittable
 *   - range may be iterated in an arbitrary order, or in parallel
 *   example:
 *     double d[10]
 *     range<double> r(d,d+10);

 *     r.Foreach([&](double & v){ r+=1.0;});
 *
 *     range<double> r1(r,tags::split());
 *
 *     auto r2=r1.split();
 *
 *     range<const double> cr(d,d+10);
 *     r.Foreach([&](double const & v){ r+=1.0;});
 *
 * @tparam _Category
 * @tparam _Tp  value_type
 * @tparam _Distance difference_type
 * @tparam _Pointer  value_type *
 * @tparam _Reference value_type &
 */

template <typename...>
struct ContinueRange;
template <typename...>
struct UnorderedRange;

template <typename T>
struct RangeBase {
    //    SP_OBJECT_BASE(RangeBase<T>);
    typedef RangeBase<T> this_type;
    typedef std::size_t size_type;

   private:
    typedef ContinueRange<T> continue_type;
    typedef UnorderedRange<T> unordered_type;

   public:
    typedef T value_type;
    virtual bool is_divisible() const { return false; }
    virtual size_type size() const { return 0; }
    virtual bool empty() const { return true; }
    virtual void ForeachOverride(std::function<void(value_type&)> const& fun) const {};

    virtual std::shared_ptr<this_type> split(tags::split const& sp) {
        //        UNIMPLEMENTED;
        return nullptr;
    }

    template <typename TFun, typename... Args>
    void Foreach(TFun const& fun, Args&&... args) const {
        if (dynamic_cast<continue_type const*>(this) != nullptr) {
            dynamic_cast<continue_type const*>(this)->DoForeach(fun, std::forward<Args>(args)...);
        } else if (dynamic_cast<unordered_type const*>(this) != nullptr) {
            dynamic_cast<unordered_type const*>(this)->DoForeach(fun, std::forward<Args>(args)...);
        } else {
            ForeachOverride([&](value_type& v) { fun(v, std::forward<Args>(args)...); });
        }
    }

    std::shared_ptr<RangeBase<T>> m_next_;
};

template <typename T>
struct Range {
    typedef Range<T> this_type;
    typedef RangeBase<T> base_type;

   public:
    typedef T value_type;

    Range() : m_next_(nullptr), m_is_full_(false) {}
    ~Range() = default;

    explicit Range(std::shared_ptr<base_type> const& p) : m_next_(p), m_is_full_(false) {}
    Range(this_type const& other) : m_next_(other.m_next_), m_is_full_(other.m_is_full_) {}
    Range(this_type&& other) noexcept : m_next_(other.m_next_), m_is_full_(other.m_is_full_) {}
    Range(this_type& other, tags::split const& s) : Range(other.split(s)) {}

    Range& operator=(this_type const& other) {
        this_type(other).swap(*this);
        return *this;
    }
    Range& operator=(this_type&& other) {
        this_type(other).swap(*this);
        return *this;
    }
    void reset(std::shared_ptr<base_type> const& p = nullptr) { m_next_ = p; }

    void swap(this_type& other) {
        std::swap(m_next_, other.m_next_);
        std::swap(m_is_full_, other.m_is_full_);
    }

    bool is_divisible() const {  // FIXME: this is not  full functional
        return m_next_ != nullptr && m_next_->is_divisible();
    }
    bool empty() const { return m_next_ == nullptr; }
    bool isNull() const { return m_next_ == nullptr; }

    void SetFull() {
        m_is_full_ = true;
        m_next_.reset();
    }
    bool isFull() const { return m_is_full_; }
    void clear() {
        m_next_.reset();
        m_is_full_ = false;
    }

    this_type split(tags::split const& s = tags::split()) {
        // FIXME: this is not  full functional
        this_type res;
        UNIMPLEMENTED;
        return std::move(res);
    }

    this_type& append(this_type const& other) { return append(other.m_next_); }

    this_type& append(this_type&& other) {
        if (!isFull()) { append(other.m_next_); }
        other.reset();
        return *this;
    }

    this_type& append(std::shared_ptr<base_type> const& other) {
        if (!isFull()) {
            auto* cursor = &m_next_;
            while ((*cursor) != nullptr) { cursor = &(*cursor)->m_next_; }
            *cursor = other;
        }
        return *this;
    }
    size_type size() const {
        size_type res = 0;
        if (isFull()) {
            res = std::numeric_limits<size_type>::max();
        } else {
            for (auto* cursor = &m_next_; *cursor != nullptr; cursor = &((*cursor)->m_next_)) {
                res += (*cursor)->size();
            }
        }
        return res;
    }
    size_type num_of_block() const {
        size_type count = 0;
        auto const* cursor = &m_next_;
        while ((*cursor) != nullptr) {
            ++count;
            cursor = &(*cursor)->m_next_;
        }
        return count;
    }
    template <typename... Args>
    void Foreach(Args&&... args) const {
        ASSERT(!isFull());
        for (auto* cursor = &m_next_; *cursor != nullptr; cursor = &((*cursor)->m_next_)) {
            (*cursor)->Foreach(std::forward<Args>(args)...);
        }
    }

    base_type const& self() const { return *m_next_; }
    std::shared_ptr<base_type> operator[](int) { return m_next_; }
    std::shared_ptr<base_type> operator[](int) const { return m_next_; }

   private:
    std::shared_ptr<base_type> m_next_ = nullptr;
    bool m_is_full_ = false;
};

template <typename T>
struct ContinueRange<T> : public RangeBase<T> {
    typedef ContinueRange<T> this_type;
    typedef RangeBase<T> base_type;
    //    SP_DEFINE_FANCY_TYPE_NAME(ContinueRange<T>, RangeBase<T>)
    typedef T value_type;
    static std::string ClassName() { return std::string("ContinueRange<") + typeid(T).name() + ">"; }

   public:
    bool is_divisible() const override { return false; }

    size_type size() const override { return 0; }

    bool empty() const override { return true; }

    void ForeachOverride(std::function<void(value_type&)> const& fun) const override { UNIMPLEMENTED; };

    std::shared_ptr<base_type> split(tags::split const& sp) override {
        UNIMPLEMENTED;
        return nullptr;
    }

    template <typename TFun, typename... Args>
    void DoForeach(TFun const& fun, Args&&... args) const {
        UNIMPLEMENTED;
    }
};

template <typename T>
struct UnorderedRange<T> : public RangeBase<T> {
    typedef UnorderedRange<T> this_type;
    typedef RangeBase<T> base_type;
    //    SP_DEFINE_FANCY_TYPE_NAME(UnorderedRange<T>, RangeBase<T>)
    typedef T value_type;

   public:
    bool is_divisible() const override { return false; }

    size_type size() const override { return 0; }

    bool empty() const override { return true; }

    void ForeachOverride(std::function<void(value_type&)> const& fun) const override { UNIMPLEMENTED; };

    std::shared_ptr<base_type> split(tags::split const& sp) override {
        UNIMPLEMENTED;
        return nullptr;
    }

    template <typename TFun, typename... Args>
    void DoForeach(TFun const& fun, Args&&... args) const {
        UNIMPLEMENTED;
    }
    void insert(value_type const& v) {}
};

template <typename TOtherRange>
struct RangeAdapter : public RangeBase<typename TOtherRange::value_type>, public TOtherRange {
    typedef RangeAdapter<TOtherRange> this_type;
    typedef RangeBase<typename TOtherRange::value_type> base_type;

    typedef typename TOtherRange::value_type value_type;

    template <typename... Args>
    RangeAdapter(Args&&... args) : TOtherRange(std::forward<Args>(args)...) {}

    RangeAdapter(TOtherRange& other, tags::split const& sp) : TOtherRange(other.split(sp)) {}

    ~RangeAdapter() override = default;

    bool is_divisible() override { return TOtherRange::is_divisible(); };

    bool empty() const override { return TOtherRange::empty(); };

    size_type size() const override { return TOtherRange::size(); }

    std::shared_ptr<base_type> split(tags::split const& sp) override {
        return std::dynamic_pointer_cast<base_type>(std::make_shared<this_type>(*this, sp));
    }
    void ForeachOverride(std::function<void(value_type&)> const& fun) const override {
        for (auto& item : *this) { fun(item); }
    };
};

template <typename TIterator>
struct IteratorRange : public RangeBase<typename std::iterator_traits<TIterator>::value_type> {
    typedef TIterator iterator;

    typedef typename std::iterator_traits<TIterator>::value_type value_type;

    typedef IteratorRange<TIterator> this_type;
    typedef RangeBase<value_type> base_type;

   public:
    IteratorRange(iterator const& b, iterator const& e) : m_b_(b), m_e_(e) { ASSERT(std::distance(m_b_, m_e_) >= 0); }

    IteratorRange(this_type& other) : m_b_(other.m_b_), m_e_(other.m_e_) {}

    IteratorRange(this_type&& other) : m_b_(other.m_b_), m_e_(other.m_e_) {}

    virtual ~IteratorRange() {}

    bool is_divisible() const { return size() > 0; }

    size_type size() const { return static_cast<size_type>(std::distance(m_e_, m_b_)); }

    bool empty() const { return size() > 0; }

    std::shared_ptr<base_type> split(tags::split const& sp) {
        iterator b = m_b_;
        m_b_ = std::distance(m_e_, m_b_) * sp.left() / (sp.left() + sp.right());
        return std::dynamic_pointer_cast<base_type>(std::make_shared<this_type>(b, m_b_));
    }

    void DoForeach(std::function<void(value_type&)> const& fun) const {
        for (auto it = m_b_; it != m_e_; ++it) { fun(*it); }
    }

   private:
    iterator m_b_, m_e_;
};

// template <typename T>
// struct Range {
//    typedef Range<T> this_type;
//    typedef RangeBase<T> base_type;
//
//   public:
//    typedef T value_type;
//
//    Range() : m_next_(nullptr) {}
//    ~Range() = default;
//
//    explicit Range(std::shared_ptr<base_type> const& p) : m_next_(p) {}
//    Range(this_type const& other) : m_next_(other.m_next_) {}
//    Range(this_type&& other) noexcept : m_next_(other.m_next_) {}
//    Range(this_type& other, tags::split const& s) : Range(other.split(s)) {}
//
//    Range& operator=(this_type const& other) {
//        this_type(other).swap(*this);
//        return *this;
//    }
//    Range& operator=(this_type&& other) {
//        this_type(other).swap(*this);
//        return *this;
//    }
//    void reset(std::shared_ptr<RangeBase<T>> const& p = nullptr) { m_next_ = p; }
//    bool isNull() const { return m_next_ == nullptr; }
//
//    void swap(this_type& other) { std::swap(m_next_, other.m_next_); }
//
//    bool is_divisible() const {  // FIXME: this is not  full functional
//        return m_next_ != nullptr && m_next_->is_divisible();
//    }
//    bool empty() const { return m_next_ == nullptr || m_next_->empty(); }
//    void clear() { m_next_ = std::make_shared<EmptyRangeBase<value_type>>(); }
//
//    this_type split(tags::split const& s = tags::split()) {
//        // FIXME: this is not  full functional
//        this_type res;
//        UNIMPLEMENTED;
//        return std::move(res);
//    }
//
//    this_type& append(this_type const& other) { return append(other.m_next_); }
//
//    this_type& append(std::shared_ptr<base_type> const& other) {
//        auto& cursor = m_next_;
//        while (cursor != nullptr) { cursor = cursor->m_next_; }
//        cursor = other;
//        return *this;
//    }
//    size_type m_count_() const {
//        size_type res = 0;
//        for (auto* cursor = &m_next_; *cursor != nullptr; cursor = &((*cursor)->m_next_)) { res +=
//        (*cursor)->m_count_();
//        }
//        return res;
//    }
//
//    template <typename... Args>
//    void Foreach (Args&&... args) const {
//        for (auto* cursor = &m_next_; *cursor != nullptr; cursor = &((*cursor)->m_next_)) {
//            (*cursor)->Foreach (std::forward<Args>(args)...);
//        }
//    }
//    RangeBase<T>& self() { return *m_next_; }
//    RangeBase<T> const& self() const { return *m_next_; }
//
//   private:
//    std::shared_ptr<RangeBase<T>> m_next_ = nullptr;
//};

template <typename T, typename... Args>
Range<T> make_continue_range(Args&&... args) {
    return std::move(Range<T>(std::make_shared<ContinueRange<T>>(std::forward<Args>...)));
};

template <typename T, typename... Args>
Range<T> make_unordered_range(Args&&... args) {
    return Range<T>(std::make_shared<UnorderedRange<T>>(std::forward<Args>...));
};

template <typename TIterator>
Range<typename std::iterator_traits<TIterator>::value_type> make_iterator_range(TIterator const& b,
                                                                                TIterator const& e) {
    return Range<typename std::iterator_traits<TIterator>::value_type>(
        std::make_shared<IteratorRange<TIterator>>(b, e));
};

template <typename TOtherRange, typename... Args>
Range<typename TOtherRange::value_type> make_range(Args&&... args) {
    return Range<typename TOtherRange::value_type>(std::make_shared<RangeAdapter<TOtherRange>>(std::forward<Args>...));
};
}
#endif  // SIMPLA_RANGE_H
